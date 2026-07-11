from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
import logging
import pandas as pd
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from recommender import (
    rerank_recommendations,
    generate_recommendation_copy,
    generate_local_fallback
)
from bandit import update_bandit_weights
from customer_store import (
    CustomerStore,
    CustomerStoreError,
    DuplicateCustomerError,
    InvalidCredentialsError,
    resolve_customer_db_path,
)
from personalization import customer_recommendations

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kfc_api")
DEMO_BACKTEST_SEED = 42

# Global in-memory cache
MENU_ITEMS_DF = pd.DataFrame(columns=['name', 'category', 'price'])
MENU_PRICE_LOOKUP = {}
PROMOTIONS_LIST = []
AFFINITY_RULES = []
CUSTOMER_STORE = None
CUSTOMER_SESSION_COOKIE = "customer_session"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global MENU_ITEMS_DF, MENU_PRICE_LOOKUP, PROMOTIONS_LIST, AFFINITY_RULES, CUSTOMER_STORE

    # Resolve paths relative to the directory containing main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "_bmad-output", "data")
    menu_path = os.path.join(data_dir, "menu.csv")
    promo_path = os.path.join(data_dir, "promotions.csv")
    rules_path = os.path.join(data_dir, "affinity_rules.json")
    db_path = os.path.join(data_dir, "kiosk.db")

    logger.info("Initializing in-memory cache on startup...")

    # The authenticated customer flow owns a separate database. It never enters
    # the kiosk rebuild pipeline or changes the kiosk's runtime data contracts.
    try:
        CUSTOMER_STORE = CustomerStore(resolve_customer_db_path())
        CUSTOMER_STORE.initialize()
        logger.info("Initialized customer account store at %s.", CUSTOMER_STORE.db_path)
    except Exception:
        CUSTOMER_STORE = None
        logger.exception("Failed to initialize the customer account store.")

    loaded_from_db = False
    if os.path.exists(db_path):
        import sqlite3
        try:
            logger.info(f"Loading runtime data from SQLite database at {db_path}...")
            conn = sqlite3.connect(db_path)

            # 1. Load Menu
            menu_query = "SELECT name, category, price, image FROM menu"
            df = pd.read_sql_query(menu_query, conn)
            required_cols = {'name', 'category', 'price'}
            if required_cols.issubset(df.columns):
                MENU_ITEMS_DF = df
                for idx, row in df.iterrows():
                    try:
                        MENU_PRICE_LOOKUP[row['name']] = float(row['price'])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid price value for item {row.get('name')}: {row.get('price')}")
                        MENU_PRICE_LOOKUP[row['name']] = 0.0
                logger.info(f"Loaded {len(MENU_ITEMS_DF)} menu items from SQLite successfully.")
            else:
                raise ValueError(f"SQLite menu table is missing required columns: {required_cols - set(df.columns)}")

            # 2. Load Promotions
            promotions_df = pd.read_sql_query("SELECT * FROM promotions", conn)
            PROMOTIONS_LIST = promotions_df.to_dict(orient="records")
            logger.info(f"Loaded {len(PROMOTIONS_LIST)} active promotions from SQLite successfully.")

            # 3. Load Affinity Rules
            cursor = conn.cursor()
            cursor.execute("SELECT antecedents, consequents, support, confidence, lift FROM affinity_rules")
            rules_rows = cursor.fetchall()
            loaded_rules = []
            for row in rules_rows:
                loaded_rules.append({
                    "antecedents": json.loads(row[0]),
                    "consequents": json.loads(row[1]),
                    "support": float(row[2]),
                    "confidence": float(row[3]),
                    "lift": float(row[4])
                })
            AFFINITY_RULES = loaded_rules
            logger.info(f"Loaded {len(AFFINITY_RULES)} association rules from SQLite successfully.")

            conn.close()
            loaded_from_db = True
        except Exception as e:
            logger.error(f"Failed to load data from SQLite: {e}. Falling back to CSV/JSON files.")
            # Clear cache to avoid partial state before fallback
            MENU_ITEMS_DF = pd.DataFrame(columns=['name', 'category', 'price'])
            MENU_PRICE_LOOKUP = {}
            PROMOTIONS_LIST = []
            AFFINITY_RULES = []

    if not loaded_from_db:
        logger.info("Initializing in-memory cache from CSV/JSON fallback...")
        # 1. Load Menu
        if os.path.exists(menu_path):
            try:
                df = pd.read_csv(menu_path)
                # Validate required columns
                required_cols = {'name', 'category', 'price'}
                if required_cols.issubset(df.columns):
                    MENU_ITEMS_DF = df
                    for idx, row in df.iterrows():
                        try:
                            MENU_PRICE_LOOKUP[row['name']] = float(row['price'])
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid price value for item {row.get('name')}: {row.get('price')}")
                            MENU_PRICE_LOOKUP[row['name']] = 0.0
                    logger.info(f"Loaded {len(MENU_ITEMS_DF)} menu items successfully.")
                else:
                    logger.error(f"menu.csv is missing required columns: {required_cols - set(df.columns)}")
            except Exception as e:
                logger.error(f"Failed to load menu.csv: {e}")
        else:
            logger.error(f"menu.csv not found at: {menu_path}")

        # 2. Load Promotions
        if os.path.exists(promo_path):
            try:
                promotions_df = pd.read_csv(promo_path)
                PROMOTIONS_LIST = promotions_df.to_dict(orient="records")
                logger.info(f"Loaded {len(PROMOTIONS_LIST)} active promotions successfully.")
            except Exception as e:
                logger.error(f"Failed to load promotions.csv: {e}")
        else:
            logger.error(f"promotions.csv not found at: {promo_path}")

        # 3. Load Affinity Rules
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    rules_data = json.load(f)
                    if isinstance(rules_data, list):
                        AFFINITY_RULES = rules_data
                        logger.info(f"Loaded {len(AFFINITY_RULES)} association rules successfully.")
                    else:
                        logger.error("affinity_rules.json is not a valid JSON array.")
            except Exception as e:
                logger.error(f"Failed to load affinity_rules.json: {e}")
        else:
            logger.error(f"affinity_rules.json not found at: {rules_path}")

    yield

    # Cleanup on shutdown (if any)
    logger.info("Shutting down KFC Kiosk Recommendation API.")

app = FastAPI(title="KFC Kiosk Recommendation API", lifespan=lifespan)

# Resolve static directory relative to main.py
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))


def _customer_cookie_options(request: Request):
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": (
            request.url.scheme == "https"
            or os.environ.get("CUSTOMER_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"}
        ),
        "path": "/",
    }


def _active_customer_store() -> CustomerStore:
    if CUSTOMER_STORE is None:
        raise HTTPException(status_code=503, detail="Customer accounts are temporarily unavailable.")
    return CUSTOMER_STORE


def _current_customer(request: Request):
    token = request.cookies.get(CUSTOMER_SESSION_COOKIE)
    customer = _active_customer_store().get_session_user(token)
    if customer is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return customer


def _catalog_for_customer_checkout():
    catalog = {}
    for row in MENU_ITEMS_DF.to_dict(orient="records"):
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        catalog[name] = {
            "price": row.get("price"),
            "category": row.get("category", ""),
        }
    return catalog


def _set_customer_session(response: JSONResponse, request: Request, token: str, expires_at: str):
    expires = datetime.fromisoformat(expires_at)
    max_age = max(0, int((expires - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        key=CUSTOMER_SESSION_COOKIE,
        value=token,
        max_age=max_age,
        **_customer_cookie_options(request),
    )


@app.get("/customer")
def read_customer_landing():
    return FileResponse(os.path.join(static_dir, "customer", "index.html"))


@app.get("/customer/login")
def read_customer_login():
    return FileResponse(os.path.join(static_dir, "customer", "login.html"))


@app.get("/customer/app")
def read_customer_app(request: Request):
    try:
        _current_customer(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse(url="/customer/login", status_code=303)
        raise
    return FileResponse(os.path.join(static_dir, "customer", "app.html"))

@app.get("/api/menu")
def get_menu():
    """Return cached menu items as a list of {name, category, price, image} objects."""
    if MENU_ITEMS_DF.empty:
        return []
    cols = ["name", "category", "price"]
    if "image" in MENU_ITEMS_DF.columns:
        cols.append("image")
    return MENU_ITEMS_DF[cols].to_dict(orient="records")

class RecommendRequest(BaseModel):
    cart_items: Optional[List[str]] = None
    timestamp: Optional[str] = None

class RecommendationResponse(BaseModel):
    name: str
    price: float
    score: float
    copy: str
    rationale: str

@app.post("/api/recommend", response_model=List[RecommendationResponse])
def recommend(request: RecommendRequest):
    # If cart_items is null/empty or timestamp is null/empty, return 200 OK with empty list
    if not request.cart_items or not request.timestamp:
        return []

    try:
        candidates = rerank_recommendations(
            cart_items=request.cart_items,
            active_promotions=PROMOTIONS_LIST,
            affinity_rules=AFFINITY_RULES,
            menu_items=MENU_ITEMS_DF,
            timestamp=request.timestamp
        )
    except Exception as e:
        logger.exception("Error in recommendation engine")
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {str(e)}")

    if not candidates:
        return []

    results = []

    # Take top 5 candidates
    top_candidates = candidates[:5]

    for idx, cand in enumerate(top_candidates):
        if not isinstance(cand, dict) or "name" not in cand or "score" not in cand:
            continue

        name = cand["name"]
        score = cand["score"]
        original_price = MENU_PRICE_LOOKUP.get(name, 0.0)
        price = float(cand.get("sale_price", original_price) or 0.0)
        promotion_context = {
            key: cand.get(key)
            for key in (
                "promo_id",
                "promotion_name",
                "discount_pct",
                "discount_label",
                "amount_off_vnd",
                "sale_price",
                "urgency",
            )
            if cand.get(key) is not None
        }

        # Exactly one API call per recommendation event:
        # Call Gemini API only for the top candidate (idx == 0).
        # For the rest, fall back to local rule-based template.
        if idx == 0:
            copy_data = generate_recommendation_copy(
                item_name=name,
                item_price=price,
                cart_items=request.cart_items,
                promotion_context=promotion_context
            )
            if not isinstance(copy_data, dict):
                copy_data = generate_local_fallback(name, price, promotion_context=promotion_context)
        else:
            copy_data = generate_local_fallback(name, price, promotion_context=promotion_context)

        results.append(RecommendationResponse(
            name=name,
            price=price,
            score=score,
            copy=copy_data.get("copy", ""),
            rationale=copy_data.get("rationale", "")
        ))

    return results


class CustomerCredentialsRequest(BaseModel):
    email: str
    password: str


class CustomerCheckoutLine(BaseModel):
    name: str
    quantity: int = Field(ge=1, le=99)


class CustomerCheckoutRequest(BaseModel):
    cart_items: List[CustomerCheckoutLine]
    offer_id: Optional[str] = None


class CustomerRecommendationResponse(RecommendationResponse):
    personalization_reason: str
    cold_start: bool
    promotion: Optional[dict] = None


class CustomerAovSimulationResponse(BaseModel):
    general_hybrid_aov: float
    personalized_aov: float
    absolute_change: float
    percentage_uplift: float
    eligible_customer_count: int
    skipped_customer_count: int
    panel_size: int
    benchmark: str
    evidence_type: str
    real_customer_sales_proof: bool
    persona_seed: Optional[int] = None
    fixture_sha256: str
    holdout_used_as_history: bool
    timestamp_policy: str
    general_promotion_treatment: str
    active_promotion_persona_count: int
    active_promotion_coverage: float
    personalized_promotion_treatment: str


def _customer_aov_replay_inputs():
    """Keep the customer replay aligned with the catalog already served by this app."""
    menu_records = MENU_ITEMS_DF.to_dict(orient="records")
    menu_category_lookup = {}
    for row in menu_records:
        name = str(row.get("name") or "").strip()
        if name:
            menu_category_lookup[name] = str(row.get("category") or "")
    return {
        "menu_records": menu_records,
        "menu_price_lookup": dict(MENU_PRICE_LOOKUP),
        "menu_category_lookup": menu_category_lookup,
        "promotions_list": list(PROMOTIONS_LIST),
        "affinity_rules": list(AFFINITY_RULES),
    }


def _customer_offer_date() -> str:
    """Return the trusted UTC date used to identify a browser-issued offer."""
    return datetime.now(timezone.utc).date().isoformat()


@app.post("/api/customer/register")
def register_customer(credentials: CustomerCredentialsRequest, http_request: Request):
    store = _active_customer_store()
    try:
        customer = store.register_user(credentials.email, credentials.password)
        token, expires_at = store.create_session(customer["id"], rotate_existing=True)
    except DuplicateCustomerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CustomerStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response = JSONResponse({"customer": customer})
    _set_customer_session(response, http_request, token, expires_at)
    return response


@app.post("/api/customer/login")
def login_customer(credentials: CustomerCredentialsRequest, http_request: Request):
    store = _active_customer_store()
    try:
        customer = store.authenticate(credentials.email, credentials.password)
        # Rotating revokes prior opaque tokens for this customer before setting a new one.
        token, expires_at = store.create_session(customer["id"], rotate_existing=True)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid email or password.") from exc
    response = JSONResponse({"customer": customer})
    _set_customer_session(response, http_request, token, expires_at)
    return response


@app.post("/api/customer/logout", status_code=204)
def logout_customer(request: Request):
    _active_customer_store().revoke_session(request.cookies.get(CUSTOMER_SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(CUSTOMER_SESSION_COOKIE, path="/")
    return response


@app.get("/api/customer/session")
def customer_session(request: Request):
    return {"customer": _current_customer(request)}


@app.get("/api/customer/aov-simulation", response_model=CustomerAovSimulationResponse)
def customer_aov_simulation(request: Request):
    _current_customer(request)
    try:
        from personalization_backtest import run_personalization_backtest

        results = run_personalization_backtest(inputs=_customer_aov_replay_inputs())
        return CustomerAovSimulationResponse(
            general_hybrid_aov=results["general_hybrid_aov"],
            personalized_aov=results["personalized_aov"],
            absolute_change=results["absolute_change"],
            percentage_uplift=results["percentage_uplift"],
            eligible_customer_count=results["eligible_customer_count"],
            skipped_customer_count=results["skipped_customer_count"],
            panel_size=results["panel_size"],
            benchmark=results["benchmark"],
            evidence_type=results["evidence_type"],
            real_customer_sales_proof=results["real_customer_sales_proof"],
            persona_seed=results.get("persona_seed"),
            fixture_sha256=results["fixture_sha256"],
            holdout_used_as_history=results["holdout_used_as_history"],
            timestamp_policy=results["timestamp_policy"],
            general_promotion_treatment=results["general_promotion_treatment"],
            active_promotion_persona_count=results["active_promotion_persona_count"],
            active_promotion_coverage=results["active_promotion_coverage"],
            personalized_promotion_treatment=results["personalized_promotion_treatment"],
        )
    except Exception:
        logger.exception("Error during customer AOV simulation")
        raise HTTPException(
            status_code=500,
            detail="Customer AOV simulation is temporarily unavailable.",
        )


@app.get("/api/customer/orders")
def customer_order_history(request: Request):
    customer = _current_customer(request)
    return {"orders": _active_customer_store().list_completed_orders(customer["id"])}


@app.post("/api/customer/checkout")
def customer_checkout(request: Request, checkout: CustomerCheckoutRequest):
    customer = _current_customer(request)
    cart_items = [
        line.model_dump() if hasattr(line, "model_dump") else line.dict()
        for line in checkout.cart_items
    ]
    try:
        order = _active_customer_store().create_completed_order(
            user_id=customer["id"],
            cart_items=cart_items,
            catalog=_catalog_for_customer_checkout(),
            offer_id=checkout.offer_id,
        )
    except CustomerStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"order": order}


@app.post("/api/customer/recommend", response_model=List[CustomerRecommendationResponse])
def customer_recommend(request: Request, recommendation_request: RecommendRequest):
    customer = _current_customer(request)
    # This edge contract intentionally mirrors /api/recommend and avoids copy/offers.
    if not recommendation_request.cart_items or not recommendation_request.timestamp:
        return []
    store = _active_customer_store()
    order_history = store.list_completed_orders(customer["id"])
    candidates = customer_recommendations(
        user_identifier=customer["id"],
        cart_items=recommendation_request.cart_items,
        timestamp=recommendation_request.timestamp,
        menu_items=MENU_ITEMS_DF,
        affinity_rules=AFFINITY_RULES,
        customer_orders=order_history,
        active_promotions=PROMOTIONS_LIST,
        offer_date=_customer_offer_date(),
        limit=5,
    )
    if not candidates:
        return []

    results = []
    for index, candidate in enumerate(candidates):
        promotion = candidate.get("promotion") if isinstance(candidate.get("promotion"), dict) else None
        if promotion and promotion.get("type") == "personal":
            try:
                promotion = store.issue_personal_offer(customer["id"], promotion)
            except CustomerStoreError as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Your personal offer changed. Please refresh recommendations.",
                ) from exc
        promotion_context = None
        if promotion:
            promotion_context = {
                "discount_pct": promotion.get("discount_pct"),
                "amount_off_vnd": promotion.get("amount_off_vnd"),
                "sale_price": promotion.get("sale_price"),
                "discount_label": promotion.get("display_text") or promotion.get("discount_label"),
                "promotion_name": promotion.get("promotion_name") or "Personal offer",
                "urgency": promotion.get("urgency"),
            }
        item_price = float(candidate.get("price", 0.0) or 0.0)
        if index == 0:
            copy_data = generate_recommendation_copy(
                item_name=candidate["name"],
                item_price=item_price,
                cart_items=recommendation_request.cart_items,
                promotion_context=promotion_context,
            )
            if not isinstance(copy_data, dict):
                copy_data = generate_local_fallback(candidate["name"], item_price, promotion_context=promotion_context)
        else:
            copy_data = generate_local_fallback(candidate["name"], item_price, promotion_context=promotion_context)
        results.append(
            CustomerRecommendationResponse(
                name=candidate["name"],
                price=item_price,
                score=float(candidate.get("score", 0.0) or 0.0),
                copy=copy_data.get("copy", ""),
                rationale=copy_data.get("rationale", ""),
                personalization_reason=candidate.get("personalization_reason", ""),
                cold_start=bool(candidate.get("cold_start")),
                promotion=promotion,
            )
        )
    return results

class BacktestResponse(BaseModel):
    baseline_aov: float
    hybrid_aov: float
    absolute_change: float
    percentage_uplift: float
    final_weights: Optional[dict] = None

@app.post("/api/backtest", response_model=BacktestResponse)
def run_backtest():
    try:
        from backtest import run_backtest_simulation
        results = run_backtest_simulation(seed=DEMO_BACKTEST_SEED)
        return BacktestResponse(
            baseline_aov=results["baseline_aov"],
            hybrid_aov=results["hybrid_aov"],
            absolute_change=results["absolute_change"],
            percentage_uplift=results["percentage_uplift"],
            final_weights=results.get("final_weights")
        )
    except Exception as e:
        logger.exception("Error during backtest simulation")
        raise HTTPException(status_code=500, detail=f"Backtest simulation error: {str(e)}")

class FeedbackContext(BaseModel):
    promo_active: bool
    time_active: bool

class FeedbackRequest(BaseModel):
    recommended_item: str
    accepted: bool
    context: FeedbackContext

@app.post("/api/recommend/feedback")
def receive_feedback(request: FeedbackRequest):
    try:
        updated_weights = update_bandit_weights(
            accepted=request.accepted,
            promo_active=request.context.promo_active,
            time_active=request.context.time_active
        )
        return {"status": "success", "updated_weights": updated_weights}
    except Exception as e:
        logger.exception("Error processing feedback")
        raise HTTPException(status_code=500, detail=f"Feedback processing error: {str(e)}")
