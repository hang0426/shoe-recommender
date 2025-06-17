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

## Setup

1. **Configuration**  
   Copy the template and create your local config file:
   ```bash
   cp config/db_config.example.json config/db_config.json
   ```
   - Edit `db_config.json` with your credentials  
   - ⚠️ Never commit this file to GitHub

2. **Environment**  
   Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Security
- Store sensitive data (passwords/API keys) in `.env`  
- Add `.env` and `config/db_config.json` to `.gitignore`
