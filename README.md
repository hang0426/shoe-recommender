# Shoe Recommender System

## Features
- Multi-brand shoe recommendations
- Precise size/width filtering
- Color preference scoring

## Quick Start
```python
from core.recommender import ShoeRecommender
import json

# Load config (remember to keep your password secret!)
with open('config/db_config.json') as f:
    db_config = json.load(f)

# Initialize recommender
recommender = ShoeRecommender(db_config)

# Get recommendations
results = recommender.recommend(
    target_gender="Women's",
    target_size=7.5,
    brand_preferences={'Nike': {'models': ['Air Force']}}
)