from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import logging
import pandas as pd
from contextlib import asynccontextmanager

from recommender import (
    rerank_recommendations,
    generate_recommendation_copy,
    generate_local_fallback
)
from bandit import update_bandit_weights

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kfc_api")

# Global in-memory cache
MENU_ITEMS_DF = pd.DataFrame(columns=['name', 'category', 'price'])
MENU_PRICE_LOOKUP = {}
PROMOTIONS_LIST = []
AFFINITY_RULES = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global MENU_ITEMS_DF, MENU_PRICE_LOOKUP, PROMOTIONS_LIST, AFFINITY_RULES
    
    # Resolve paths relative to the directory containing main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "_bmad-output", "data")
    menu_path = os.path.join(data_dir, "menu.csv")
    promo_path = os.path.join(data_dir, "promotions.csv")
    rules_path = os.path.join(data_dir, "affinity_rules.json")
    
    logger.info("Initializing in-memory cache on startup...")
    
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
        price = MENU_PRICE_LOOKUP.get(name, 0.0)
        
        # Exactly one API call per recommendation event:
        # Call Gemini API only for the top candidate (idx == 0).
        # For the rest, fall back to local rule-based template.
        if idx == 0:
            copy_data = generate_recommendation_copy(
                item_name=name,
                item_price=price,
                cart_items=request.cart_items
            )
            if not isinstance(copy_data, dict):
                copy_data = generate_local_fallback(name, price)
        else:
            copy_data = generate_local_fallback(name, price)
            
        results.append(RecommendationResponse(
            name=name,
            price=price,
            score=score,
            copy=copy_data.get("copy", ""),
            rationale=copy_data.get("rationale", "")
        ))
        
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
        results = run_backtest_simulation(seed=42)
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

