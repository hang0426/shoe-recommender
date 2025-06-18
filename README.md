# 👟 Shoe Recommender System

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

A smart recommendation engine for footwear selection based on brand preferences, sizing accuracy, and style matching.

## ✨ Features
- **Multi-brand recommendations** (Nike, Adidas, etc.)
- **Precision sizing** with width/arch type support
- **Color preference scoring** algorithm
- **Personalized ranking** based on wishlist history
- **REST API endpoint** for integration

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/shoe-recommender.git
cd shoe-recommender

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```python
from core.recommender import ShoeRecommender
import json

# Initialize with your configuration
with open('config/db_config.json') as f:
    db_config = json.load(f)

recommender = ShoeRecommender(db_config)

# Get personalized recommendations
results = recommender.recommend(
    target_gender="Women's",
    target_size=7.5,
    target_width="Medium",
    brand_preferences={
        'nike': {'models': ['dunk'], 'exclude': ['air max']},
        'puma': {'models': ['rs-x']},
        'new balance': {}
    },
    color_preferences=['pink', 'beige', 'white']
)

print(results.top(5))  # Display top 5 matches
```

## ⚙️ Configuration

1. **Setup Config File**
   ```bash
   cp config/db_config.example.json config/db_config.json
   ```
   Edit the new file with your database credentials:
   ```json
   {
     "host": "your-database-host",
     "port": 5432,
     "dbname": "db_name",
     "user": "your_username",
     "password": "your_password"  # Never commit this!
   }
   ```

2. **Environment Variables**  
   For API keys or sensitive data:
   ```bash
   echo 'API_KEY=your_real_key_here' >> .env
   ```

## 🔒 Security Best Practices
- Add these to your `.gitignore`:
  ```gitignore
  # Config files
  config/db_config.json
  *.env
  
  # Python
  __pycache__/
  *.py[cod]
  ```
- Use environment variables for production:
  ```python
  import os
  db_password = os.getenv('DB_PASSWORD')  # Instead of hardcoding
  ```
