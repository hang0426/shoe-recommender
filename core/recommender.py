import psycopg2
import pandas as pd
import json
import re
from psycopg2 import sql

class ShoeRecommender:
    """
    Advanced shoe recommendation system with:
    - Database connectivity
    - Multi-brand and model support
    - Precise size/width filtering
    - Tiered scoring algorithm
    """
    
    def __init__(self, db_config):
        """
        Initialize database connection and load data
        
        Args:
            db_config (dict): Database configuration containing:
                - user: Database username
                - password: Database password
                - host: Database host
                - port: Database port
                - dbname: Database name
        """
        self.conn = self._connect_db(db_config)
        self.df = self._load_data(db_config.get('schema'))
        self.width_compatibility = {
            'narrow': {'exact': ['narrow'], 'compatible': ['medium (regular)', 'regular']},
            'medium': {'exact': ['medium (regular)', 'regular'], 'compatible': []},
            'wide': {'exact': ['wide'], 'compatible': ['medium (regular)', 'extra wide']},
            'extra wide': {'exact': ['extra wide'], 'compatible': ['wide']}
        }
            
    def _connect_db(self, db_config):
        """Establish database connection"""
        try:
            conn = psycopg2.connect(
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                port=db_config['port'],
                dbname=db_config['dbname'],
                sslmode='require'
            )
            print("Database connection successful")
            return conn
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise
            
    def _load_data(self, schema="wishlist_data"):
        """Load and preprocess product data from wishlist schema"""
        # Set schema
        with self.conn.cursor() as cursor:
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                
        # Query product data
        query = sql.SQL("""
            SELECT product_id, product_name, partner_id, category, 
                   size, color, quantity, options, vendor, metadata 
            FROM wishlist_products
            WHERE partner_id = %s AND category = %s AND quantity >= %s
        """)
        
        with self.conn.cursor() as cursor:
            cursor.execute(query, (306, 'Apparel & Accessories > Shoes', 1))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        # Apply all preprocessing steps
        df = self._preprocess_data(df)
        return df
        
    def _preprocess_data(self, df):
        """Execute all data preprocessing steps"""
        # Extract colors from product name
        df = self._extract_color_from_name(df)
        
        # Expand JSON columns
        df, _ = self._expand_options_columns(df)
        df, _ = self._expand_metadata_columns(df)
        
        # Extract gender/department
        df = self._extract_gender(df)
        
        # Standardize column names
        df = self._standardize_columns(df)
        
        return df
    
    def _extract_color_from_name(self, df):
        """Extract color information from product name"""
        def _split_colors(name):
            try:
                parts = name.split(',')
                if len(parts) >= 3:
                    color_str = parts[1].strip()
                    return [c.strip() for c in color_str.split('/')]
                return []
            except Exception:
                return []
                
        df = df.copy()
        df['color_from_name'] = df['product_name'].apply(_split_colors)
        return df
    
    def _expand_options_columns(self, df, col='options'):
        """Expand JSON options column into separate columns"""
        def _parse_options(option_str):
            try:
                if isinstance(option_str, str):
                    if not option_str.strip():
                        return {}
                    return json.loads(option_str)
                elif isinstance(option_str, dict):
                    return option_str
                return {}
            except Exception as e:
                print(f"Options parse error: {e}")
                return {}
                
        parsed = df[col].apply(_parse_options)
        options_df = pd.DataFrame(parsed.tolist(), index=df.index)
        
        # Handle column conflicts
        for col in options_df.columns:
            if col in df.columns:
                df = df.drop(columns=[col])
                
        return pd.concat([df, options_df], axis=1), list(options_df.columns)
    
    def _expand_metadata_columns(self, df, col='metadata'):
        """Expand metadata column into separate columns"""
        selected_keys = [
            "custom.color", "custom.model", "google.gender",
            "my_fields.size", "my_fields.width"
        ]
        
        def _extract_metadata(meta_str):
            try:
                if isinstance(meta_str, str):
                    meta_dict = json.loads(meta_str)
                elif isinstance(meta_str, dict):
                    meta_dict = meta_str
                else:
                    return {k: None for k in selected_keys}
                return {k: meta_dict.get(k) for k in selected_keys}
            except Exception as e:
                print(f"Metadata parse error: {e}")
                return {k: None for k in selected_keys}
                
        parsed = df[col].apply(_extract_metadata)
        meta_df = pd.DataFrame(parsed.tolist(), index=df.index)
        
        return pd.concat([df, meta_df], axis=1), list(meta_df.columns)
    
    def _extract_gender(self, df):
        """Extract gender information from product name"""
        def _get_gender(name):
            if not isinstance(name, str):
                return 'Unknown'
            match = re.search(r"\b(Women's|Men's|Unisex|Kids')\b", name)
            return match.group(1) if match else 'Unknown'
            
        df['gender_from_name'] = df['product_name'].apply(_get_gender)
        return df
    
    def _standardize_columns(self, df):
        """Standardize column names across data sources"""
        column_mapping = {
            'Size': 'size_from_options',
            'Color': 'color_from_options',
            'Width': 'width_from_options',
            'Model': 'model_from_options',
            'first_word': 'first_word_from_name',
            'Department': 'gender_from_name'
        }
        return df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    def recommend(self, target_gender, target_size, target_width=None,
                 brand_preferences=None, color_preferences=None, top_k=10):
        """
        Generate shoe recommendations based on criteria
        
        Args:
            target_gender: Target gender (Men's/Women's/etc.)
            target_size: Target shoe size
            target_width: Target width (optional)
            brand_preferences: Dict of {brand: {models: [], exclude: []}} 
            color_preferences: List of colors in priority order
            top_k: Number of results to return
            
        Returns:
            DataFrame of recommended products
        """
        # Initialize parameters
        df = self.df.copy()
        brand_preferences = brand_preferences or {}
        color_preferences = color_preferences or []
        target_width = target_width or ""
        empty_result = pd.DataFrame(columns=df.columns.tolist() + ['score'])
        
        # 1. Apply gender filter
        if 'gender_from_name' not in df.columns:
            return empty_result
            
        df = df[df['gender_from_name'].str.lower() == target_gender.lower()]
        if df.empty:
            return empty_result
            
        # 2. Process and filter sizes
        def parse_size(size_str):
            if pd.isna(size_str):
                return (None, None, False)
            try:
                if '-' in size_str:
                    low, high = map(lambda x: x.replace('.', '').strip(), size_str.split('-'))
                    low = float(low) + 0.5 if low.endswith('.') else float(low)
                    high = float(high) + 0.5 if high.endswith('.') else float(high)
                    return (low - 0.5, high + 0.5, True)
                else:
                    val = float(size_str.replace('.', '')) + 0.5 if str(size_str).endswith('.') else float(size_str)
                    return (val - 0.5, val + 0.5, False)
            except:
                return (None, None, False)
                
        df[['size_min', 'size_max', 'is_range']] = df['my_fields.size'].apply(
            lambda x: pd.Series(parse_size(x))
        
        try:
            target_size = float(target_size)
            size_mask = (
                (df['size_min'] <= target_size) & 
                (df['size_max'] >= target_size)
            df = df[size_mask].copy()
        except:
            return pd.DataFrame(columns=df.columns)

        if df.empty:
            return df
            
        # 3. Apply width filter if specified
        if target_width:
            target_width_lower = target_width.lower()
            if target_width_lower in self.width_compatibility:
                valid_widths = (
                    self.width_compatibility[target_width_lower]['exact'] +
                    self.width_compatibility[target_width_lower]['compatible'])
                df = df[df['my_fields.width'].apply(
                    lambda x: str(x).lower() in valid_widths)]
            
        # 4. Apply brand/model filters
        if brand_preferences:
            def brand_model_check(row):
                vendor = str(row['vendor']).lower()
                model = str(row.get('custom.model', '')).lower()
                
                for brand, prefs in brand_preferences.items():
                    if brand.lower() == vendor:
                        if 'models' in prefs and prefs['models']:
                            if not any(req.lower() in model for req in prefs['models']):
                                return False
                        return True
                return False
                
            df = df[df.apply(brand_model_check, axis=1)]
            
        # 5. Score and sort results
        def compute_score(row):
            score = 0
            vendor = str(row['vendor']).lower()
            model = str(row.get('custom.model', '')).lower()
            width = str(row.get('my_fields.width', '')).lower()
            
            # Size Score (31.25 max)
            if row['is_range']:
                if row['size_min'] <= target_size <= row['size_max']:
                    score += 18.75
            else:
                size_val = float(row['size_min']) + 0.5
                if abs(size_val - target_size) < 0.01:
                    score += 31.25
                elif abs(size_val - target_size) == 0.5:
                    score += 21.875

            # Width Score (12.5 max)
            if target_width:
                target_width_lower = target_width.lower()
                if target_width_lower in self.width_compatibility:
                    if width in self.width_compatibility[target_width_lower]['exact']:
                        score += 12.5
                    elif width in self.width_compatibility[target_width_lower]['compatible']:
                        score += 6.25

            # Brand & Model Score (50 max)
            brand_matched = False
            for brand, prefs in brand_preferences.items():
                if brand.lower() == vendor:
                    brand_matched = True
                    score += 25
                    if 'models' in prefs and prefs['models']:
                        if any(req.lower() in model for req in prefs['models']):
                            score += 25
                    break

            # Color Score (6.25 max)
            if color_preferences and pd.notna(row.get('custom.color')):
                colors = [c.strip().lower() for c in str(row['custom.color']).split('/')]
                for i, product_color in enumerate(colors):
                    if product_color in [c.lower() for c in color_preferences]:
                        score += 6.25 - (i * 1.25)
                        break
                    
            return score
            
        df['score'] = df.apply(compute_score, axis=1)
        df = df.sort_values(['score', 'quantity'], ascending=[False, False])
        
        return df.head(top_k)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")
