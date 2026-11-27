"""
Precompute sentiment cache for the sample dataset so ReviewSense loads instantaneously.
"""
import pandas as pd
from model_service import sentiment_service
from column_detector import detect_columns
from analysis_engine import clean_dataset

df = pd.read_csv("data/product_reviews_and_sale.csv")
cols = detect_columns(df)
text_col = cols["text_column"]
df_clean, summary = clean_dataset(df, text_col)

print(f"Cleaning: {summary}")
texts = df_clean["_cleaned_text"].tolist()
print(f"Precomputing {len(texts)} reviews ({len(set(texts))} unique)...")
results = sentiment_service.predict_batch(texts)
sentiment_service._save_disk_cache()
print("Precomputation finished and saved to disk cache!")
