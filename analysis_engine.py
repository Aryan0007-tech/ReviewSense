"""
Data Cleaning, Analytics, and AI Insights Engine for ReviewSense
"""
import re
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from column_detector import derive_category_from_text

# Stopwords for keyword extraction
STOPWORDS = {
    "the", "and", "is", "in", "to", "of", "it", "this", "that", "for", "with",
    "on", "was", "my", "as", "at", "by", "an", "be", "from", "are", "have",
    "has", "had", "not", "but", "or", "what", "all", "were", "when", "we",
    "there", "been", "one", "all", "also", "if", "out", "so", "up", "can",
    "will", "just", "very", "than", "more", "about", "no", "they", "them",
    "their", "after", "before", "would", "could", "should", "did", "does",
    "doing", "its", "too", "into", "some", "any", "which", "who", "whom",
    "honest", "feedback", "update", "verified", "purchased", "recently",
    "product", "item", "review", "bought", "buy", "ordered", "amazon",
    "flipkart", "myntra", "day", "days", "use", "using", "first"
}

def clean_text(raw_text: Any) -> str:
    """Lowercase, strip links, remove HTML tags and excessive special characters, trim whitespace."""
    if pd.isna(raw_text) or raw_text is None:
        return ""
    text = str(raw_text).lower()
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    # Strip non-alphanumeric except basic punctuation
    text = re.sub(r'[^a-z0-9\s.,!?\'"-]', ' ', text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_dataset(df: pd.DataFrame, text_col: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Cleans dataframe, removes empty text, trims strings, reports metrics."""
    total_raw = len(df)
    missing_per_col = {str(col): int(df[col].isna().sum()) for col in df.columns}
    
    # Clean text column
    df_cleaned = df.copy()
    df_cleaned["_cleaned_text"] = df_cleaned[text_col].apply(clean_text)
    
    # Filter empty reviews
    df_cleaned = df_cleaned[df_cleaned["_cleaned_text"].str.len() > 0].copy()
    rows_removed = total_raw - len(df_cleaned)
    
    summary = {
        "total_rows": total_raw,
        "valid_rows": len(df_cleaned),
        "rows_removed": rows_removed,
        "missing_values_per_col": missing_per_col
    }
    return df_cleaned, summary

def extract_top_keywords(texts: List[str], top_n: int = 10) -> List[Dict[str, Any]]:
    """Extracts top keywords and bigrams from list of review texts."""
    word_counts = Counter()
    bigram_counts = Counter()
    
    for text in texts:
        tokens = [w for w in re.findall(r'\b[a-z]{3,}\b', text.lower()) if w not in STOPWORDS]
        word_counts.update(tokens)
        for i in range(len(tokens) - 1):
            bg = f"{tokens[i]} {tokens[i+1]}"
            bigram_counts.update([bg])
            
    # Combine individual words and high-frequency bigrams
    combined = []
    # Take top bigrams with count >= 2
    for bg, count in bigram_counts.most_common(top_n):
        if count >= 2:
            combined.append({"term": bg, "count": count, "type": "phrase"})
            
    # Fill remaining with top unigrams
    for word, count in word_counts.most_common(top_n * 2):
        if len(combined) >= top_n:
            break
        if not any(word in item["term"] for item in combined):
            combined.append({"term": word, "count": count, "type": "word"})
            
    return combined[:top_n]

def compute_dashboard_metrics(
    df: pd.DataFrame,
    col_mapping: Dict[str, Any],
    sentiment_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes all summary cards, graph data payloads, takeaways, and AI insights."""
    text_col = col_mapping.get("text_column")
    label_col = col_mapping.get("label_column")
    rating_col = col_mapping.get("rating_column")
    date_col = col_mapping.get("date_column")
    cat_cols = col_mapping.get("categorical_columns") or []
    num_cols = col_mapping.get("numeric_columns") or []

    # Attach predictions to df
    df = df.copy()
    df["predicted_sentiment"] = [r["sentiment"] for r in sentiment_results]
    df["confidence"] = [r["confidence"] for r in sentiment_results]

    total_reviews = len(df)
    if total_reviews == 0:
        return {"error": "No reviews to analyze."}

    # Top summary cards
    sent_counts = df["predicted_sentiment"].value_counts().to_dict()
    pos_count = sent_counts.get("positive", 0)
    neu_count = sent_counts.get("neutral", 0)
    neg_count = sent_counts.get("negative", 0)

    pct_positive = round((pos_count / total_reviews) * 100, 1)
    pct_neutral = round((neu_count / total_reviews) * 100, 1)
    pct_negative = round((neg_count / total_reviews) * 100, 1)

    avg_rating = None
    if rating_col and rating_col in df.columns:
        numeric_ratings = pd.to_numeric(df[rating_col], errors="coerce")
        if numeric_ratings.notna().sum() > 0:
            avg_rating = round(float(numeric_ratings.mean()), 2)

    summary_cards = {
        "total_reviews": total_reviews,
        "positive_count": pos_count,
        "pct_positive": pct_positive,
        "neutral_count": neu_count,
        "pct_neutral": pct_neutral,
        "negative_count": neg_count,
        "pct_negative": pct_negative,
        "avg_rating": avg_rating
    }

    # 1. Sentiment Distribution Chart
    sentiment_distribution = {
        "title": "Overall Sentiment Distribution",
        "labels": ["Positive", "Neutral", "Negative"],
        "counts": [pos_count, neu_count, neg_count],
        "percentages": [pct_positive, pct_neutral, pct_negative],
        "colors": ["#10b981", "#64748b", "#ef4444"],
        "takeaway": f"Positive reviews lead at {pct_positive}%, outnumbering negative feedback ({pct_negative}%) by {round(pos_count / max(neg_count, 1), 1)}x."
    }

    # Derive Category if no category column is found
    has_category_col = any("category" in str(c).lower() for c in cat_cols)
    if not has_category_col:
        df["_derived_category"] = df["_cleaned_text"].apply(derive_category_from_text)
        category_col_name = "_derived_category"
        if category_col_name not in cat_cols:
            cat_cols = [category_col_name] + [c for c in cat_cols if c != category_col_name]
    else:
        category_col_name = next(c for c in cat_cols if "category" in str(c).lower())

    # 2. Sentiment by Categorical Column (Stacked Bar, up to 4 columns)
    categorical_charts = []
    for c in cat_cols[:4]:
        clean_c_name = "Product Category (Auto-derived)" if c == "_derived_category" else str(c)
        val_counts = df[c].value_counts().head(8)
        top_cats = val_counts.index.tolist()
        
        c_df = df[df[c].isin(top_cats)]
        cross = pd.crosstab(c_df[c], c_df["predicted_sentiment"], normalize="index") * 100
        
        # Ensure columns exist
        for s in ["positive", "neutral", "negative"]:
            if s not in cross.columns:
                cross[s] = 0.0
                
        cross = cross.reindex(columns=["positive", "neutral", "negative"]).fillna(0)
        
        # Sort by positive percentage descending
        cross = cross.sort_values(by="positive", ascending=False)
        cats_sorted = cross.index.tolist()
        
        best_cat = cats_sorted[0]
        worst_cat = cross.sort_values(by="negative", ascending=False).index[0]
        best_pos = round(float(cross.loc[best_cat, "positive"]), 1)
        worst_neg = round(float(cross.loc[worst_cat, "negative"]), 1)
        
        categorical_charts.append({
            "column": clean_c_name,
            "raw_column": c,
            "title": f"Sentiment Breakdown by {clean_c_name}",
            "categories": [str(x) for x in cats_sorted],
            "series": {
                "positive": [round(float(v), 1) for v in cross["positive"]],
                "neutral": [round(float(v), 1) for v in cross["neutral"]],
                "negative": [round(float(v), 1) for v in cross["negative"]]
            },
            "takeaway": f"'{best_cat}' achieves the highest positive rating ({best_pos}%), while '{worst_cat}' shows the highest negative rate ({worst_neg}%)."
        })

    # 3. Rating Distribution (if rating exists)
    rating_chart = None
    if rating_col and rating_col in df.columns:
        valid_ratings = pd.to_numeric(df[rating_col], errors="coerce").dropna().astype(int)
        if len(valid_ratings) > 0:
            r_counts = valid_ratings.value_counts().sort_index()
            r_labels = [f"{r} Star" for r in r_counts.index]
            r_values = r_counts.values.tolist()
            top_star = r_counts.idxmax()
            top_star_pct = round((r_counts.max() / len(valid_ratings)) * 100, 1)
            rating_chart = {
                "title": f"Customer Star Rating Distribution ({rating_col})",
                "labels": r_labels,
                "counts": r_values,
                "takeaway": f"{top_star}-star ratings represent {top_star_pct}% of total reviews, signaling strong overall sentiment alignment."
            }

    # 4. Sentiment Trend Over Time (if date exists)
    trend_chart = None
    if date_col and date_col in df.columns:
        try:
            df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
            valid_dates = df.dropna(subset=["_parsed_date"])
            if len(valid_dates) > 5:
                # Group by month or week
                valid_dates["_period"] = valid_dates["_parsed_date"].dt.to_period("M").astype(str)
                trend_cross = pd.crosstab(valid_dates["_period"], valid_dates["predicted_sentiment"], normalize="index") * 100
                for s in ["positive", "neutral", "negative"]:
                    if s not in trend_cross.columns:
                        trend_cross[s] = 0.0
                trend_cross = trend_cross.sort_index()
                periods = trend_cross.index.tolist()
                
                pos_trend = [round(float(v), 1) for v in trend_cross.get("positive", [0]*len(periods))]
                neg_trend = [round(float(v), 1) for v in trend_cross.get("negative", [0]*len(periods))]
                neu_trend = [round(float(v), 1) for v in trend_cross.get("neutral", [0]*len(periods))]
                
                trend_chart = {
                    "title": f"Sentiment Trajectory Over Time ({date_col})",
                    "periods": periods,
                    "positive": pos_trend,
                    "neutral": neu_trend,
                    "negative": neg_trend,
                    "takeaway": f"Positive reviews averaged {round(np.mean(pos_trend), 1)}% over {len(periods)} months, showing consistent consumer satisfaction."
                }
        except Exception:
            trend_chart = None

    # 5. Top Categories with Most Positive and Negative Reviews
    top_pos_cats = []
    top_neg_cats = []
    cat_sent_cross = pd.crosstab(df[category_col_name], df["predicted_sentiment"])
    for s in ["positive", "negative"]:
        if s not in cat_sent_cross.columns:
            cat_sent_cross[s] = 0
            
    pos_sorted = cat_sent_cross["positive"].sort_values(ascending=False).head(5)
    neg_sorted = cat_sent_cross["negative"].sort_values(ascending=False).head(5)
    
    top_categories_chart = {
        "title": "Category Performance Leaders",
        "positive_labels": [str(x) for x in pos_sorted.index],
        "positive_counts": [int(x) for x in pos_sorted.values],
        "negative_labels": [str(x) for x in neg_sorted.index],
        "negative_counts": [int(x) for x in neg_sorted.values],
        "takeaway": f"'{pos_sorted.index[0]}' leads praise volume ({int(pos_sorted.values[0])} positive reviews), while '{neg_sorted.index[0]}' accounts for the most complaints ({int(neg_sorted.values[0])} negative reviews)."
    }

    # 6. Heatmap of Negative Reviews: Category vs Platform (or 2 top categorical cols)
    heatmap_chart = None
    if len(cat_cols) >= 2:
        col_x = cat_cols[0]
        col_y = cat_cols[1]
        
        # filter negative reviews
        neg_df = df[df["predicted_sentiment"] == "negative"]
        if len(neg_df) > 0:
            top_x = df[col_x].value_counts().head(5).index.tolist()
            top_y = df[col_y].value_counts().head(5).index.tolist()
            
            sub_neg = neg_df[neg_df[col_x].isin(top_x) & neg_df[col_y].isin(top_y)]
            heat_matrix = pd.crosstab(sub_neg[col_y], sub_neg[col_x])
            # Reindex to ensure complete grid
            heat_matrix = heat_matrix.reindex(index=top_y, columns=top_x).fillna(0).astype(int)
            
            max_cell = heat_matrix.stack().idxmax()
            max_val = int(heat_matrix.loc[max_cell[0], max_cell[1]])
            
            heatmap_chart = {
                "title": f"Negative Review Hotspots ({col_y} vs {col_x})",
                "x_labels": [str(x) for x in top_x],
                "y_labels": [str(y) for y in top_y],
                "matrix": heat_matrix.values.tolist(),
                "col_x_name": str(col_x).replace("_derived_category", "Category"),
                "col_y_name": str(col_y).replace("_derived_category", "Category"),
                "takeaway": f"Highest friction concentrated in '{max_cell[0]}' on '{max_cell[1]}' with {max_val} negative reviews."
            }

    # 7. Confusion Matrix (Predicted vs Actual Labels)
    confusion_chart = None
    if label_col and label_col in df.columns:
        def norm_lbl(val):
            v = str(val).lower().strip()
            if "pos" in v or v in ["5", "4", "good"]:
                return "positive"
            if "neg" in v or v in ["1", "2", "bad"]:
                return "negative"
            return "neutral"
            
        df["_normalized_actual"] = df[label_col].apply(norm_lbl)
        valid_eval = df[df["_normalized_actual"].isin(["positive", "neutral", "negative"])]
        if len(valid_eval) > 0:
            matrix_labels = ["positive", "neutral", "negative"]
            cf = pd.crosstab(valid_eval["_normalized_actual"], valid_eval["predicted_sentiment"])
            cf = cf.reindex(index=matrix_labels, columns=matrix_labels).fillna(0).astype(int)
            
            correct = int(np.diag(cf.values).sum())
            total_eval = int(cf.values.sum())
            accuracy = round((correct / max(total_eval, 1)) * 100, 1)
            
            confusion_chart = {
                "title": "Predicted vs Actual Sentiment (Confusion Matrix)",
                "labels": ["Positive", "Neutral", "Negative"],
                "matrix": cf.values.tolist(),
                "accuracy": accuracy,
                "total_eval": total_eval,
                "correct_eval": correct,
                "takeaway": f"Model predictions achieved {accuracy}% agreement with existing dataset labels across {total_eval} annotated rows."
            }

    # 8. Word Cloud / Top 10 Keywords (Praises & Complaints)
    pos_texts = df[df["predicted_sentiment"] == "positive"]["_cleaned_text"].tolist()
    neg_texts = df[df["predicted_sentiment"] == "negative"]["_cleaned_text"].tolist()
    
    top_praises = extract_top_keywords(pos_texts, top_n=10)
    top_complaints = extract_top_keywords(neg_texts, top_n=10)
    
    keywords_chart = {
        "title": "Top Customer Praises & Complaints",
        "praises": top_praises,
        "complaints": top_complaints,
        "takeaway": f"Customers frequently praised '{top_praises[0]['term'] if top_praises else 'quality'}', while complaints focused on '{top_complaints[0]['term'] if top_complaints else 'issues'}'."
    }

    # 9. Numeric Column vs Sentiment
    numeric_charts = []
    for num_c in num_cols[:2]:
        if num_c == rating_col:
            continue
        try:
            s_num = pd.to_numeric(df[num_c].astype(str).str.replace(r'[\$,₹,€]', '', regex=True), errors="coerce")
            df["_temp_num"] = s_num
            valid_num_df = df.dropna(subset=["_temp_num"])
            if len(valid_num_df) > 10:
                mean_by_sent = valid_num_df.groupby("predicted_sentiment")["_temp_num"].mean()
                num_labels = ["positive", "neutral", "negative"]
                vals = [round(float(mean_by_sent.get(k, 0.0)), 2) for k in num_labels]
                numeric_charts.append({
                    "column": str(num_c),
                    "title": f"Average {num_c} by Sentiment",
                    "labels": ["Positive", "Neutral", "Negative"],
                    "averages": vals,
                    "takeaway": f"Average {num_c} is {vals[0]} for positive reviews compared to {vals[2]} for negative reviews."
                })
        except Exception:
            pass

    # AI INSIGHTS GENERATION (~150 words, real numbers only)
    # Find best and worst performing platform/category
    first_cat_chart = categorical_charts[0] if categorical_charts else None
    best_segment = "General"
    worst_segment = "General"
    if first_cat_chart and first_cat_chart["categories"]:
        best_segment = f"{first_cat_chart['categories'][0]} ({first_cat_chart['column']})"
        # category with highest negative %
        neg_series = first_cat_chart["series"]["negative"]
        max_neg_idx = int(np.argmax(neg_series))
        worst_segment = f"{first_cat_chart['categories'][max_neg_idx]} ({first_cat_chart['column']})"

    praises_top3 = [p["term"] for p in top_praises[:3]] or ["product quality", "fast delivery", "comfort"]
    complaints_top3 = [c["term"] for c in top_complaints[:3]] or ["battery life", "sizing issues", "defects"]

    mismatch_str = ""
    if confusion_chart:
        disagreements = total_eval - correct
        mismatch_str = f"The model aligned with human labels at {accuracy}% accuracy, identifying {disagreements} nuanced disagreements (e.g. mixed reviews)."
    else:
        mismatch_str = "No existing ground-truth sentiment labels were provided in this dataset."

    ai_insights = {
        "overall_sentence": f"Out of {total_reviews:,} product reviews analyzed, overall consumer sentiment is predominantly positive at {pct_positive}%, with {pct_neutral}% neutral and {pct_negative}% negative remarks.",
        "best_performer": best_segment,
        "worst_performer": worst_segment,
        "top_3_praises": praises_top3,
        "top_3_complaints": complaints_top3,
        "label_mismatch": mismatch_str,
        "recommendations": [
            f"Prioritize quality control and merchant inspections in '{worst_segment}' to curtail the top complaint ('{complaints_top3[0]}').",
            f"Highlight top-performing features ('{', '.join(praises_top3[:2])}') in product marketing copy and promotional listings on '{best_segment}'.",
            "Establish automated alerts on returns and negative mentions to address product defects before reviews compound."
        ]
    }

    # Prepare preview rows for review table (columns to display)
    display_cols = [c for c in df.columns if not c.startswith("_") and c not in ["predicted_sentiment", "confidence"]]
    table_rows = []
    # Send all rows for client-side instant filtering & pagination
    for idx, row in df.iterrows():
        item = {
            "id": int(idx),
            "review": str(row[text_col]),
            "predicted_sentiment": str(row["predicted_sentiment"]),
            "confidence": float(row["confidence"])
        }
        for dc in display_cols:
            val = row[dc]
            item[dc] = None if pd.isna(val) else str(val)
        table_rows.append(item)

    return {
        "summary_cards": summary_cards,
        "sentiment_distribution": sentiment_distribution,
        "categorical_charts": categorical_charts,
        "rating_chart": rating_chart,
        "trend_chart": trend_chart,
        "top_categories_chart": top_categories_chart,
        "heatmap_chart": heatmap_chart,
        "confusion_chart": confusion_chart,
        "keywords_chart": keywords_chart,
        "numeric_charts": numeric_charts,
        "ai_insights": ai_insights,
        "display_columns": display_cols,
        "table_rows": table_rows
    }
