from core.recommender import ShoeRecommender
import json
import pandas as pd
import pytest  # if you don't have this package，need pip install pytest

def load_test_cases():
    """Define test cases"""
    return [
        {
            "name": "Men's Asics Gel-Kayano Size 10",
            "target_gender": "Men's",
            "target_size": 10,
            "target_width": None,
            "brand_preferences": {'Asics': {'models': ['Gel-Kayano']}},
            "color_preferences": ['White', 'Blue'],
            "top_k": 5,
            "expected_columns": [
                'product_id', 'product_name', 'gender_from_name', 
                'my_fields.size', 'my_fields.width', 'vendor',
                'custom.model', 'custom.color', 'score'
            ]
        },
        {
            "name": "Women's Hoka Torrent Size 8",
            "target_gender": "Women's",
            "target_size": 8,
            "target_width": None,
            "brand_preferences": {'Hoka': {'models': ['Torrent']}},
            "color_preferences": ['Yellow', 'Orange'],
            "top_k": 5,
            "expected_columns": [
                'product_id', 'product_name', 'gender_from_name', 
                'my_fields.size', 'my_fields.width', 'vendor',
                'custom.model', 'custom.color', 'score'
            ]
        }
    ]

def test_recommendations():
    with open('../config/db_config.json') as f:
        db_config = json.load(f)
    
    recommender = ShoeRecommender(db_config)
    test_cases = load_test_cases()
    
    for case in test_cases:
        print(f"\n=== Testing: {case['name']} ===")
        
        # Execute
        results = recommender.recommend(
            target_gender=case["target_gender"],
            target_size=case["target_size"],
            target_width=case["target_width"],
            brand_preferences=case["brand_preferences"],
            color_preferences=case["color_preferences"],
            top_k=case["top_k"]
        )
        
        # Validate
        assert isinstance(results, pd.DataFrame), "Result should be a DataFrame"
        
        missing_cols = [col for col in case["expected_columns"] 
                      if col not in results.columns]
        assert not missing_cols, f"Missing columns: {missing_cols}"
        
        assert len(results) <= case["top_k"], "Should return no more than top_k"
        
        # Print
        print(f"Test passed! Returned {len(results)} recommendations")
        if not results.empty:
            print("Top recommendation:")
            print(results.iloc[0][['product_name', 'vendor', 'score']])
        else:
            print("Warning: No results returned for this test case")

def run_manual_checks():
    """Print more detailed results"""
    with open('../config/db_config.json') as f:
        db_config = json.load(f)
    
    recommender = ShoeRecommender(db_config)
    test_cases = load_test_cases()
    
    for case in test_cases:
        print(f"\n=== Detailed Output for: {case['name']} ===")
        
        results = recommender.recommend(
            target_gender=case["target_gender"],
            target_size=case["target_size"],
            target_width=case["target_width"],
            brand_preferences=case["brand_preferences"],
            color_preferences=case["color_preferences"],
            top_k=case["top_k"]
        )
        
        if not results.empty:
            print(results[case["expected_columns"]].head())
        else:
            print("No results found for this query")

if __name__ == "__main__":
    print("Running automated tests...")
    test_recommendations()
    
    print("\nWould you like to see detailed results? (y/n)")
    if input().lower() == 'y':
        run_manual_checks()
