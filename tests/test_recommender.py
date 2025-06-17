from core.recommender import ShoeRecommender
import json
import pandas as pd

def test_recommendation():
    with open('../config/db_config.json') as f:
        db_config = json.load(f)
    
    recommender = ShoeRecommender(db_config)
    results = recommender.recommend(
        target_gender="Men's",
        target_size=8,
        top_k=3
    )
    assert isinstance(results, pd.DataFrame)
    print("Test passed! Sample results:")
    print(results.head())

if __name__ == "__main__":
    test_recommendation()