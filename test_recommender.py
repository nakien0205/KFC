import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from recommender import rerank_recommendations

class TestRecommender(unittest.TestCase):
    def setUp(self):
        # Sample menu items
        self.menu = [
            {"item_id": "ITEM_001", "name": "Burger Zinger", "category": "Burgers", "price": 56000.0},
            {"item_id": "ITEM_002", "name": "French Fries", "category": "Sides", "price": 20000.0},
            {"item_id": "ITEM_003", "name": "Pepsi", "category": "Drinks", "price": 13000.0},
            {"item_id": "ITEM_004", "name": "1 Eggtart", "category": "Desserts", "price": 20000.0},
            {"item_id": "ITEM_005", "name": "Combo 1 Fried Chicken", "category": "Combos", "price": 59000.0},
        ]
        
        # Sample promotions
        self.promotions = [
            {"promo_id": "PROMO_001", "name": "Lunch Special Burger Combo", "discount_pct": 15, "start_date": "2026-06-01", "end_date": "2026-08-31"},
            {"promo_id": "PROMO_004", "name": "Dessert Delight", "discount_pct": 20, "start_date": "2026-05-01", "end_date": "2026-12-31"},
        ]
        
        # Sample affinity rules
        self.rules = [
            {
                "antecedents": ["Burger Zinger"],
                "consequents": ["French Fries"],
                "confidence": 0.70,
                "support": 0.10,
                "lift": 2.0
            },
            {
                "antecedents": ["Burger Zinger"],
                "consequents": ["Pepsi"],
                "confidence": 0.60,
                "support": 0.08,
                "lift": 1.5
            },
            {
                "antecedents": ["Combo 1 Fried Chicken"],
                "consequents": ["1 Eggtart"],
                "confidence": 0.50,
                "support": 0.05,
                "lift": 1.2
            }
        ]
        
        # Patch load_bandit_weights to return default weights for test reproducibility
        self.patcher = patch('recommender.load_bandit_weights')
        self.mock_load_weights = self.patcher.start()
        self.mock_load_weights.return_value = {
            "alpha_promo": 2.0,
            "beta_promo": 8.0,
            "alpha_time": 1.5,
            "beta_time": 8.5
        }

    def tearDown(self):
        self.patcher.stop()

    def test_base_confidence_only(self):
        # Cart has Burger Zinger. No promo active, non-peak hour (e.g. 15:00)
        # Rules matching: Burger Zinger -> French Fries (0.70), Burger Zinger -> Pepsi (0.60)
        # Expected scores: French Fries: 0.70 * 1.0 * 1.0 = 0.70, Pepsi: 0.60 * 1.0 * 1.0 = 0.60
        timestamp = "2026-07-06T15:00:00+07:00"
        cart = ["Burger Zinger"]
        
        recs = rerank_recommendations(cart, self.promotions, self.rules, self.menu, timestamp)
        
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["name"], "French Fries")
        self.assertAlmostEqual(recs[0]["score"], 0.70)
        self.assertEqual(recs[1]["name"], "Pepsi")
        self.assertAlmostEqual(recs[1]["score"], 0.60)

    def test_exclusion_constraint(self):
        # Cart has Burger Zinger and French Fries.
        # Rules matching: Burger Zinger -> French Fries (filtered out because already in cart), Burger Zinger -> Pepsi (0.60)
        timestamp = "2026-07-06T15:00:00+07:00"
        cart = ["Burger Zinger", "French Fries"]
        
        recs = rerank_recommendations(cart, self.promotions, self.rules, self.menu, timestamp)
        
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["name"], "Pepsi")

    def test_promo_boost_only(self):
        # Cart has Combo 1 Fried Chicken.
        # Match: Combo 1 Fried Chicken -> 1 Eggtart (0.50)
        # 1 Eggtart is Dessert. Dessert Delight is active on 2026-07-06.
        # Boost: Promo_Boost = 0.20. Time_Boost = 0.0 (non-peak 15:00).
        # Expected score: 0.50 * 1.20 * 1.0 = 0.60
        timestamp = "2026-07-06T15:00:00+07:00"
        cart = ["Combo 1 Fried Chicken"]
        
        recs = rerank_recommendations(cart, self.promotions, self.rules, self.menu, timestamp)
        
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["name"], "1 Eggtart")
        self.assertAlmostEqual(recs[0]["score"], 0.60)

    def test_time_boost_only(self):
        # Cart has Burger Zinger.
        # Match: Burger Zinger -> French Fries (0.70) (Sides), Burger Zinger -> Pepsi (0.60) (Drinks)
        # Time: 12:00 (Lunch peak hour 11:00-14:00). Boost category: Burgers, Combos.
        # Neither French Fries (Sides) nor Pepsi (Drinks) is Burgers/Combos.
        # Wait, let's add a rule: Burger Zinger -> Combo 1 Fried Chicken (0.40) (Combos).
        # Expected boost for Combo 1 Fried Chicken: Time_Boost = 0.15. Promo_Boost = 0.0.
        # Score = 0.40 * 1.0 * 1.15 = 0.46.
        # Let's adjust rules in test case:
        local_rules = self.rules + [
            {
                "antecedents": ["Burger Zinger"],
                "consequents": ["Combo 1 Fried Chicken"],
                "confidence": 0.40,
                "support": 0.05,
                "lift": 1.1
            }
        ]
        timestamp = "2026-07-06T12:00:00+07:00"
        cart = ["Burger Zinger"]
        
        recs = rerank_recommendations(cart, self.promotions, local_rules, self.menu, timestamp)
        
        # Check Combo 1 Fried Chicken has time boost
        combo_rec = next(r for r in recs if r["name"] == "Combo 1 Fried Chicken")
        self.assertAlmostEqual(combo_rec["score"], 0.46)
        
        # Check French Fries (Sides) has no boost at lunch
        fries_rec = next(r for r in recs if r["name"] == "French Fries")
        self.assertAlmostEqual(fries_rec["score"], 0.70)

    def test_multiplicative_scoring_both_boosts(self):
        # Cart has Burger Zinger.
        # Match: Burger Zinger -> French Fries (0.70) (Sides)
        # Time: 18:00 (Dinner peak hour 17:00-21:00). Boost categories: Combos, Sides.
        # French Fries is in Sides category. Time_Boost = 0.15.
        # Let's add an active promotion for Sides (e.g. Dessert Delight style Sides promo, or modify promotions)
        local_promotions = self.promotions + [
            {"promo_id": "PROMO_005", "name": "Sides Discount", "discount_pct": 10, "start_date": "2026-07-01", "end_date": "2026-07-31"}
        ]
        timestamp = "2026-07-06T18:00:00+07:00"
        cart = ["Burger Zinger"]
        
        recs = rerank_recommendations(cart, local_promotions, self.rules, self.menu, timestamp)
        
        fries_rec = next(r for r in recs if r["name"] == "French Fries")
        # Expected: 0.70 * (1 + 0.20) * (1 + 0.15) = 0.70 * 1.20 * 1.15 = 0.966
        self.assertAlmostEqual(fries_rec["score"], 0.966)

    def test_deduplication_highest_score(self):
        # If multiple rules point to the same consequents:
        # Rule 1: A -> C (confidence 0.50)
        # Rule 2: B -> C (confidence 0.60)
        # Cart has A and B. Expected: recommend C once with score from Rule 2.
        local_rules = [
            {"antecedents": ["Burger Zinger"], "consequents": ["French Fries"], "confidence": 0.50, "support": 0.05, "lift": 1.2},
            {"antecedents": ["Pepsi"], "consequents": ["French Fries"], "confidence": 0.60, "support": 0.06, "lift": 1.3}
        ]
        timestamp = "2026-07-06T15:00:00+07:00"
        cart = ["Burger Zinger", "Pepsi"]
        
        recs = rerank_recommendations(cart, self.promotions, local_rules, self.menu, timestamp)
        
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["name"], "French Fries")
        self.assertAlmostEqual(recs[0]["score"], 0.60)

    def test_promo_hour_validation(self):
        # Lunch Special Burger Combo contains "Lunch" in name.
        # Active date: 2026-07-06.
        # Let's test at 18:00 (Dinner, non-lunch).
        # Expected: Lunch Special promo is NOT active. Promo_Boost should be 0.0.
        # Match: Burger Zinger -> Combo 1 Fried Chicken (0.40) (Combos)
        # Combo 1 Fried Chicken is Combos category, which gets Time_Boost (+0.15) at Dinner (18:00).
        # Expected score: 0.40 * 1.0 * 1.15 = 0.46 (no promo boost).
        local_rules = [
            {"antecedents": ["Burger Zinger"], "consequents": ["Combo 1 Fried Chicken"], "confidence": 0.40}
        ]
        timestamp = "2026-07-06T18:00:00+07:00"
        cart = ["Burger Zinger"]
        
        recs = rerank_recommendations(cart, self.promotions, local_rules, self.menu, timestamp)
        combo_rec = next(r for r in recs if r["name"] == "Combo 1 Fried Chicken")
        self.assertAlmostEqual(combo_rec["score"], 0.46)

    def test_over_broad_chicken_exclusion(self):
        # "Free Fried Chicken" promo should boost fried chicken, NOT chicken burger/pasta/rice.
        # We test with a chicken burger candidate item: "Chicken Burger Deluxe" (Burgers category)
        # and a fried chicken candidate item: "1 pc Fried Chicken" (Sides category).
        local_promotions = [
            {"promo_id": "PROMO_006", "name": "Free Fried Chicken", "discount_pct": 100, "start_date": "2026-07-01", "end_date": "2026-07-31"}
        ]
        local_menu = [
            {"name": "Chicken Burger Deluxe", "category": "Burgers"},
            {"name": "1 pc Fried Chicken", "category": "Sides"}
        ]
        local_rules = [
            {"antecedents": ["Pepsi"], "consequents": ["Chicken Burger Deluxe"], "confidence": 0.50},
            {"antecedents": ["Pepsi"], "consequents": ["1 pc Fried Chicken"], "confidence": 0.50}
        ]
        timestamp = "2026-07-06T15:00:00+07:00" # non-peak
        cart = ["Pepsi"]
        
        recs = rerank_recommendations(cart, local_promotions, local_rules, local_menu, timestamp)
        
        burger_rec = next(r for r in recs if r["name"] == "Chicken Burger Deluxe")
        chicken_rec = next(r for r in recs if r["name"] == "1 pc Fried Chicken")
        
        # Burger should get 0.50 (no promo boost)
        self.assertAlmostEqual(burger_rec["score"], 0.50)
        # Fried Chicken should get 0.50 * 1.20 = 0.60
        self.assertAlmostEqual(chicken_rec["score"], 0.60)

    def test_timezone_safety(self):
        # Verify aware timezone Z and positive offset work and do not crash with TypeError
        local_rules = [
            {"antecedents": ["Burger Zinger"], "consequents": ["French Fries"], "confidence": 0.50}
        ]
        cart = ["Burger Zinger"]
        
        # Z timezone
        recs_z = rerank_recommendations(cart, self.promotions, local_rules, self.menu, "2026-07-06T12:00:00Z")
        self.assertEqual(len(recs_z), 1)
        
        # Explicit positive offset
        recs_offset = rerank_recommendations(cart, self.promotions, local_rules, self.menu, "2026-07-06T12:00:00+07:00")
        self.assertEqual(len(recs_offset), 1)

    def test_none_input_safety(self):
        # Verify None values do not crash the recommender
        recs = rerank_recommendations(None, None, None, None, None)
        self.assertEqual(recs, [])

    def test_local_fallback_generator(self):
        from recommender import generate_local_fallback
        res = generate_local_fallback("French Fries", 20000.0)
        self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")
        self.assertEqual(res["rationale"], "Thường được mua kèm với các sản phẩm trong giỏ hàng.")

    @patch('requests.post')
    def test_gemini_success_path(self, mock_post):
        from recommender import generate_recommendation_copy
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"copy": "Ăn kèm Khoai tây chiên cho trọn vị!", "rationale": "68% khách hàng mua kèm khoai tây chiên"}'
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"], api_key="fake-key")
        self.assertEqual(res["copy"], "Ăn kèm Khoai tây chiên cho trọn vị!")
        self.assertEqual(res["rationale"], "68% khách hàng mua kèm khoai tây chiên")
        mock_post.assert_called_once()
        
    @patch('requests.post')
    def test_gemini_timeout_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        import requests
        # Mock timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"], api_key="fake-key")
        self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")
        self.assertEqual(res["rationale"], "Thường được mua kèm với các sản phẩm trong giỏ hàng.")
        
    @patch('requests.post')
    def test_gemini_error_status_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        # Mock 500 error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"], api_key="fake-key")
        self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")
        
    @patch('requests.post')
    def test_gemini_missing_key_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        # We patch os.environ to make sure GEMINI_API_KEY and USE_OLLAMA are missing/false
        with patch.dict('os.environ', {}, clear=True):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"], api_key=None)
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")

    @patch('requests.post')
    def test_gemini_non_string_cart_items(self, mock_post):
        from recommender import generate_recommendation_copy
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"USE_OLLAMA": "false"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger", 123, None], api_key="fake-key")
            # Should gracefully return fallback copy
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")

    @patch('requests.post')
    def test_ollama_success_path(self, mock_post):
        from recommender import generate_recommendation_copy
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": '{"copy": "Ăn kèm Khoai tây chiên cho trọn vị!", "rationale": "68% khách hàng mua kèm khoai tây chiên"}'
            }
        }
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"USE_OLLAMA": "true"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Ăn kèm Khoai tây chiên cho trọn vị!")
            self.assertEqual(res["rationale"], "68% khách hàng mua kèm khoai tây chiên")

    @patch('requests.post')
    def test_ollama_timeout_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        import requests
        
        # Mock timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        with patch.dict('os.environ', {"USE_OLLAMA": "true"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")

    @patch('requests.post')
    def test_ollama_connection_failure_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        import requests
        
        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with patch.dict('os.environ', {"USE_OLLAMA": "true"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")

    @patch('requests.post')
    def test_ollama_routing_no_gemini_key(self, mock_post):
        from recommender import generate_recommendation_copy
        
        # Mock response from Ollama
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": '{"copy": "Ăn kèm Khoai tây chiên cho trọn vị!", "rationale": "68% khách hàng mua kèm khoai tây chiên"}'
            }
        }
        mock_post.return_value = mock_response
        
        # Clear Gemini key from environment using patch.dict
        with patch.dict('os.environ', {}, clear=True):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Ăn kèm Khoai tây chiên cho trọn vị!")
            # Ensure the call hit the Ollama /api/chat URL and not Gemini
            call_url = mock_post.call_args[0][0]
            self.assertIn("/api/chat", call_url)

    @patch('requests.post')
    def test_openrouter_success_path(self, mock_post):
        from recommender import generate_recommendation_copy
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"copy": "Ăn kèm Khoai tây chiên giòn rụm!", "rationale": "Được gợi ý vì bạn thích Burger"}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"OPENROUTER_API_KEY": "sk-or-v1-testkey"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Ăn kèm Khoai tây chiên giòn rụm!")
            self.assertEqual(res["rationale"], "Được gợi ý vì bạn thích Burger")
            
            # Verify it hits OpenRouter endpoint
            call_url = mock_post.call_args[0][0]
            self.assertEqual(call_url, "https://openrouter.ai/api/v1/chat/completions")
            
            # Verify headers
            headers = mock_post.call_args[1]["headers"]
            self.assertEqual(headers["Authorization"], "Bearer sk-or-v1-testkey")

    @patch('requests.post')
    def test_openrouter_timeout_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        import requests
        
        mock_post.side_effect = requests.exceptions.Timeout("OpenRouter timed out")
        
        with patch.dict('os.environ', {"OPENROUTER_API_KEY": "sk-or-v1-testkey"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")
            self.assertEqual(res["rationale"], "Thường được mua kèm với các sản phẩm trong giỏ hàng.")

    @patch('requests.post')
    def test_openrouter_error_status_fallback(self, mock_post):
        from recommender import generate_recommendation_copy
        
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {"OPENROUTER_API_KEY": "sk-or-v1-testkey"}):
            res = generate_recommendation_copy("French Fries", 20000.0, ["Burger Zinger"])
            self.assertEqual(res["copy"], "Hoàn thành bữa ăn! Thêm French Fries chỉ với 20.000đ")

if __name__ == "__main__":
    unittest.main()
