import os
import json
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

def unique_rule_consequents(rules_list):
    return sorted({
        item
        for rule in rules_list
        for item in rule.get("consequents", [])
    })

def load_existing_consequent_coverage(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return unique_rule_consequents(json.load(f))
    except (json.JSONDecodeError, TypeError, OSError):
        return []

def load_report_baseline_coverage(path):
    if not os.path.exists(path):
        return []
    sections = {
        "added": [],
        "removed": [],
        "after": [],
    }
    current = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line == "## Added Consequents":
                    current = "added"
                elif line == "## Removed Consequents":
                    current = "removed"
                elif line == "## After Consequents":
                    current = "after"
                elif line.startswith("## "):
                    current = None
                elif current and line.startswith("- ") and line != "- None":
                    sections[current].append(line[2:])
    except OSError:
        return []
    baseline = (set(sections["after"]) | set(sections["removed"])) - set(sections["added"])
    return sorted(baseline)

def write_coverage_report(before_items, after_items, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    added = sorted(set(after_items) - set(before_items))
    removed = sorted(set(before_items) - set(after_items))
    lines = [
        "# Rule Consequent Coverage Report",
        "",
        "This report compares unique menu items that appear as association-rule consequents before and after the latest mining run.",
        "",
        f"Before unique consequents: {len(before_items)}",
        f"After unique consequents: {len(after_items)}",
        f"Net change: {len(after_items) - len(before_items):+d}",
        "",
        "## Added Consequents",
        "",
    ]
    lines.extend([f"- {item}" for item in added] or ["- None"])
    lines.extend(["", "## Removed Consequents", ""])
    lines.extend([f"- {item}" for item in removed] or ["- None"])
    lines.extend(["", "## After Consequents", ""])
    lines.extend([f"- {item}" for item in after_items] or ["- None"])
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def mine_affinity():
    orders_path = "_bmad-output/data/orders.csv"
    rules_path = "_bmad-output/data/affinity_rules.json"
    coverage_path = "_bmad-output/data/rule_coverage_report.md"
    before_consequents = (
        load_report_baseline_coverage(coverage_path)
        or load_existing_consequent_coverage(rules_path)
    )
    if not os.path.exists(orders_path):
        print(f"Error: {orders_path} not found. Run generate_data.py first.")
        return
        
    df_orders = pd.read_csv(orders_path)
    
    # Create basket of one-hot encoded items per transaction
    basket = pd.crosstab(df_orders['order_id'], df_orders['item_name'])
    basket = basket.astype(bool)
    
    # Mine rules with dynamic threshold fallbacks
    min_support = 0.05
    min_confidence = 0.50
    rules = pd.DataFrame()
    
    while round(min_support, 4) >= 0.01:
        print(f"Mining with min_support={min_support:.2f}, min_confidence={min_confidence:.2f}...")
        frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)
        if not frequent_itemsets.empty:
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
            if len(rules) >= 5:
                print(f"Successfully mined {len(rules)} association rules.")
                break
        min_support -= 0.01
        min_confidence = max(0.10, min_confidence - 0.05)
        
    target_consequents = 20
    fallback_thresholds = [
        (0.005, 0.08),
        (0.003, 0.05),
    ]
    for fallback_support, fallback_confidence in fallback_thresholds:
        current_consequents = set()
        if not rules.empty:
            singleton_rules = rules[rules["consequents"].apply(lambda items: len(items) == 1)]
            current_consequents = {
                item
                for consequent in singleton_rules["consequents"]
                for item in consequent
            }
        if len(rules) >= 5 and len(current_consequents) >= target_consequents:
            break

        print(
            "Fallback to coverage thresholds "
            f"min_support={fallback_support:.3f}, min_confidence={fallback_confidence:.2f}..."
        )
        frequent_itemsets = apriori(basket, min_support=fallback_support, use_colnames=True)
        if not frequent_itemsets.empty:
            rules = association_rules(
                frequent_itemsets,
                metric="confidence",
                min_threshold=fallback_confidence
            )
            
    rules_list = []
    if not rules.empty:
        rules = rules[rules["consequents"].apply(lambda items: len(items) == 1)]
        # Sort for kiosk usefulness: reliable confidence first, then support and lift.
        rules = rules.sort_values(by=["confidence", "support", "lift"], ascending=False)
        for idx, row in rules.iterrows():
            rules_list.append({
                "antecedents": list(row["antecedents"]),
                "consequents": list(row["consequents"]),
                "support": float(row["support"]),
                "confidence": float(row["confidence"]),
                "lift": float(row["lift"]),
                "leverage": float(row["leverage"]) if "leverage" in row else None,
                "conviction": float(row["conviction"]) if "conviction" in row else None
            })
            
    after_consequents = unique_rule_consequents(rules_list)

    # Save rules to root directory and data directory
    for output_path in ["affinity_rules.json", "_bmad-output/data/affinity_rules.json"]:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(rules_list, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(rules_list)} rules to {output_path}")
        except Exception as e:
            print(f"Error saving to {output_path}: {e}")

    write_coverage_report(before_consequents, after_consequents, coverage_path)
    print(
        "Rule consequent coverage: "
        f"{len(before_consequents)} before -> {len(after_consequents)} after "
        f"({len(after_consequents) - len(before_consequents):+d})"
    )
    print(f"Saved coverage report to {coverage_path}")

if __name__ == "__main__":
    mine_affinity()
