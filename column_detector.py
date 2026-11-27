"""
Automatic Column Detector & Classifier for ReviewSense
"""
import re
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Keywords for categorizing reviews if no product category column is present
CATEGORY_KEYWORDS = {
    "Electronics & Gadgets": [
        "phone", "laptop", "battery", "screen", "charging", "charger", "cable",
        "audio", "sound", "headphone", "earphone", "bluetooth", "display", "device",
        "tablet", "camera", "speaker", "tv", "monitor", "mic", "wireless"
    ],
    "Fashion & Apparel": [
        "size", "fit", "fabric", "cloth", "shirt", "dress", "jeans", "shoes",
        "wear", "cotton", "color", "material", "stitching", "comfort", "sneakers",
        "t-shirt", "jacket", "pants", "heel", "strap"
    ],
    "Home & Kitchen": [
        "kitchen", "pan", "cooker", "bed", "sheet", "pillow", "furniture",
        "knife", "bottle", "cleaning", "room", "sofa", "table", "chair", "mattress",
        "blender", "oven", "curtain", "lamp"
    ],
    "Beauty & Personal Care": [
        "skin", "hair", "face", "cream", "lotion", "serum", "fragrance",
        "perfume", "scent", "shampoo", "wash", "glow", "oil", "moisturizer",
        "makeup", "lipstick"
    ],
    "Books & Media": [
        "book", "author", "read", "pages", "story", "novel", "print", "cover",
        "writing", "chapter"
    ],
    "Sports & Fitness": [
        "gym", "workout", "fitness", "yoga", "mat", "weight", "exercise",
        "grip", "running", "sport", "band", "bottle"
    ]
}

def derive_category_from_text(text: str) -> str:
    """Derive rough product category from keywords in review text."""
    if not isinstance(text, str):
        return "General"
    t = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', t))
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "General"

def detect_columns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Inspects dataframe and identifies:
    1. Review text column (longest average text length among string columns)
    2. Sentiment label column (positive/neutral/negative or 1-5 rating)
    3. Categorical columns (low cardinality, e.g. platform, category, region, brand)
    4. Numeric columns (rating, price, sales, quantity)
    5. Date column
    """
    cols = list(df.columns)
    total_rows = len(df)
    
    text_col = None
    label_col = None
    date_col = None
    rating_col = None
    categorical_cols = []
    numeric_cols = []
    
    avg_str_lens = {}
    sentiment_values = {"positive", "neutral", "negative", "pos", "neu", "neg", "good", "bad", "okay"}
    
    for col in cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        col_lower = str(col).lower()
        
        # Check if Date
        is_date = False
        if any(d_kw in col_lower for d_kw in ["date", "time", "timestamp", "created", "day"]):
            try:
                pd.to_datetime(series.head(50), errors="raise")
                date_col = col
                is_date = True
            except Exception:
                pass
        elif series.dtype == "object":
            # Test sample
            try:
                converted = pd.to_datetime(series.head(30), format="mixed", errors="coerce")
                if converted.notna().sum() > 20:
                    date_col = col
                    is_date = True
            except Exception:
                pass
                
        if is_date:
            continue
            
        # Check if Numeric
        is_numeric = False
        if pd.api.types.is_numeric_dtype(series):
            is_numeric = True
        else:
            # Check if strings can be numeric
            try:
                numeric_series = pd.to_numeric(series.astype(str).str.replace(r'[\$,₹,€]', '', regex=True).str.strip(), errors="coerce")
                if numeric_series.notna().sum() / len(series) > 0.85:
                    is_numeric = True
            except Exception:
                pass
                
        if is_numeric:
            # Check if it could be a 1-5 rating
            unique_vals = set(series.unique())
            if unique_vals.issubset({1, 2, 3, 4, 5, 1.0, 2.0, 3.0, 4.0, 5.0}) or ("rating" in col_lower or "score" in col_lower or "stars" in col_lower):
                if rating_col is None:
                    rating_col = col
            numeric_cols.append(col)
            continue
            
        # String / Object column
        str_series = series.astype(str)
        mean_len = str_series.apply(len).mean()
        avg_str_lens[col] = mean_len
        
        # Check if Sentiment Label column
        unique_lowers = set(str_series.str.lower().str.strip().unique())
        if len(unique_lowers) <= 6 and (
            unique_lowers.issubset(sentiment_values) or 
            any(s in col_lower for s in ["sentiment", "label", "target", "polarity", "truth"])
        ):
            if label_col is None:
                label_col = col
                
        # Check if Categorical
        unique_count = len(unique_lowers)
        if 1 < unique_count <= 50 and unique_count < total_rows * 0.5:
            if col != label_col and mean_len < 40 and not any(id_kw in col_lower for id_kw in ["id", "uuid", "hash", "key"]):
                categorical_cols.append(col)

    # Detect review text column: column with the longest average text length
    if avg_str_lens:
        sorted_by_len = sorted(avg_str_lens.items(), key=lambda x: x[1], reverse=True)
        # Avoid picking the label column as text column
        for c, _ in sorted_by_len:
            if c != label_col:
                text_col = c
                break
        if not text_col and sorted_by_len:
            text_col = sorted_by_len[0][0]
            
    # Filter out text_col and label_col from categorical
    categorical_cols = [c for c in categorical_cols if c != text_col and c != label_col]
    
    # Priority order for categorical columns (platform, category, brand, window, etc.)
    def cat_priority(c):
        cl = str(c).lower()
        if any(k in cl for k in ["platform", "window", "site", "source"]):
            return 1
        if any(k in cl for k in ["category", "dept", "product_type", "type"]):
            return 2
        if any(k in cl for k in ["brand", "seller", "vendor"]):
            return 3
        return 10
        
    categorical_cols = sorted(categorical_cols, key=cat_priority)

    return {
        "text_column": text_col,
        "label_column": label_col,
        "rating_column": rating_col,
        "date_column": date_col,
        "categorical_columns": categorical_cols,
        "numeric_columns": numeric_cols,
        "all_columns": cols
    }
