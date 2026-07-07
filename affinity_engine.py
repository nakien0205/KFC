import os
import json
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

def mine_affinity():
    orders_path = "_bmad-output/data/orders.csv"
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
        
    if rules.empty:
        # Fallback to minimal support/confidence to guarantee rules are mined
        print("Fallback to minimal thresholds...")
        frequent_itemsets = apriori(basket, min_support=0.005, use_colnames=True)
        if not frequent_itemsets.empty:
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.10)
            
    rules_list = []
    if not rules.empty:
        # Sort rules by lift and confidence descending
        rules = rules.sort_values(by=["lift", "confidence"], ascending=False)
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
            
    # Save rules to root directory and data directory
    for output_path in ["affinity_rules.json", "_bmad-output/data/affinity_rules.json"]:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(rules_list, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(rules_list)} rules to {output_path}")
        except Exception as e:
            print(f"Error saving to {output_path}: {e}")

if __name__ == "__main__":
    mine_affinity()
