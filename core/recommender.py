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
            
    def _load_data(self, schema=None):
        """Load and preprocess product data"""
        # Set schema if specified
        if schema:
            with self.conn.cursor() as cursor:
                cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                
        # Query product data
        query = sql.SQL("""
            SELECT product_id, product_name, partner_id, category, 
                   size, color, quantity, options, vendor, metadata 
            FROM Products
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
        
        # 1. Apply gender filter
        df = df[df['gender_from_name'].str.lower() == target_gender.lower()]
        if df.empty:
            return pd.DataFrame(columns=df.columns)
            
        # 2. Process and filter sizes
        df = self._filter_by_size(df, target_size)
        if df.empty:
            return df
            
        # 3. Apply width filter if specified
        if target_width:
            df = self._filter_by_width(df, target_width)
            
        # 4. Apply brand/model filters
        if brand_preferences:
            df = self._filter_by_brand(df, brand_preferences)
            
        # 5. Score and sort results
        df = self._score_products(
            df, target_size, target_width,
            brand_preferences, color_preferences
        )
        
        return df.head(top_k)
        
    def _filter_by_size(self, df, target_size):
        """Filter products by size range"""
        def _parse_size(size_str):
            if pd.isna(size_str):
                return None, None, False
            try:
                if '-' in size_str:
                    low, high = map(lambda x: x.replace('.', '').strip(), size_str.split('-'))
                    low = float(low) + 0.5 if low.endswith('.') else float(low)
                    high = float(high) + 0.5 if high.endswith('.') else float(high)
                    return low - 0.5, high + 0.5, True
                else:
                    val = float(size_str.replace('.', '')) + 0.5 if str(size_str).endswith('.') else float(size_str)
                    return val - 0.5, val + 0.5, False
            except:
                return None, None, False
                
        df[['size_min', 'size_max', 'is_range']] = df['my_fields.size'].apply(
            lambda x: pd.Series(_parse_size(x))
        )
        
        try:
            target_size = float(target_size)
            size_mask = (
                (df['size_min'] <= target_size) & 
                (df['size_max'] >= target_size)
            )
            return df[size_mask].copy()
        except:
            return pd.DataFrame(columns=df.columns)
            
    def _filter_by_width(self, df, target_width):
        """Filter products by width compatibility"""
        width_compatibility = {
            'narrow': {'exact': ['narrow'], 'compatible': ['medium (regular)', 'regular']},
            'medium': {'exact': ['medium (regular)', 'regular'], 'compatible': []},
            'wide': {'exact': ['wide'], 'compatible': ['medium (regular)', 'extra wide']},
            'extra wide': {'exact': ['extra wide'], 'compatible': ['wide']}
        }
        
        target_width = target_width.lower()
        valid_widths = (
            width_compatibility.get(target_width, {}).get('exact', []) +
            width_compatibility.get(target_width, {}).get('compatible', [])
        )
        
        return df[
            df['my_fields.width'].apply(
                lambda x: str(x).lower() in valid_widths
            )
        ]
        
    def _filter_by_brand(self, df, brand_preferences):
        """Filter products by brand/model requirements"""
        def _check_brand(row):
            vendor = str(row['vendor']).lower()
            model = str(row.get('custom.model', '')).lower()
            
            for brand, prefs in brand_preferences.items():
                if brand.lower() == vendor:
                    if 'models' in prefs and prefs['models']:
                        if not any(req.lower() in model for req in prefs['models']):
                            return False
                    if 'exclude' in prefs and prefs['exclude']:
                        if any(excl.lower() in model for excl in prefs['exclude']):
                            return False
                    return True
            return False
            
        return df[df.apply(_check_brand, axis=1)]
        
    def _score_products(self, df, target_size, target_width, 
                       brand_preferences, color_preferences):
        """Score products based on match quality"""
        def _compute_score(row):
            score = 0
            vendor = str(row['vendor']).lower()
            model = str(row.get('custom.model', '')).lower()
            width = str(row.get('my_fields.width', '')).lower()
            
            # Size score (50 max)
            if row['is_range']:
                if row['size_min'] <= target_size <= row['size_max']:
                    score += 40
            else:
                size_val = float(row['size_min']) + 0.5
                if abs(size_val - target_size) < 0.01:
                    score += 50
                elif abs(size_val - target_size) == 0.5:
                    score += 45
            
            # Width score (30 max)
            if target_width:
                target_width_lower = target_width.lower()
                if target_width_lower in self.width_compatibility:
                    if width in self.width_compatibility[target_width_lower]['exact']:
                        score += 30
                    elif width in self.width_compatibility[target_width_lower]['compatible']:
                        score += 20
            
            # Brand/model score (60 max)
            brand_matched = False
            for brand, prefs in brand_preferences.items():
                if brand.lower() == vendor:
                    brand_matched = True
                    score += 50
                    if 'models' in prefs and prefs['models']:
                        if any(req.lower() in model for req in prefs['models']):
                            score += 20
                    break
            
            # Color score (20 max)
            if color_preferences and pd.notna(row.get('custom.color')):
                colors = [c.strip().lower() for c in str(row['custom.color']).split('/')]
                for i, target_color in enumerate(color_preferences):
                    if target_color.lower() in colors:
                        score += 20 - (i * 5)
                        break
            
            return score
            
        df['score'] = df.apply(_compute_score, axis=1)
        return df.sort_values(['score', 'quantity'], ascending=[False, False])
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")
