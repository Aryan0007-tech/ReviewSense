"""
ReviewSense - Main FastAPI Application
"""
import io
import os
import uuid
import logging
from typing import Dict, Any, Optional
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from column_detector import detect_columns
from analysis_engine import clean_dataset, compute_dashboard_metrics
from model_service import sentiment_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewSenseApp")

app = FastAPI(title="ReviewSense", description="Sentiment Analysis for E-commerce Product Reviews", version="1.0.0")

# In-memory session store for datasets
session_store: Dict[str, Dict[str, Any]] = {}

# Ensure static and data directories exist
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "product_reviews_and_sale.csv")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

class PredictSingleRequest(BaseModel):
    text: str

class AnalyzeRequest(BaseModel):
    upload_id: str
    column_mapping: Dict[str, Any]

@app.get("/")
def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ReviewSense API is running. Place index.html in static/"}

@app.get("/api/sample")
def load_sample_dataset():
    """Loads and analyzes the built-in sample dataset so the dashboard is immediately ready."""
    try:
        if not os.path.exists(SAMPLE_CSV_PATH):
            raise HTTPException(status_code=404, detail="Sample dataset not found.")
            
        df = pd.read_csv(SAMPLE_CSV_PATH)
        cols = detect_columns(df)
        text_col = cols["text_column"]
        if not text_col:
            raise HTTPException(status_code=400, detail="Could not identify review text column in sample dataset.")
            
        df_clean, cleaning_summary = clean_dataset(df, text_col)
        
        # Predict sentiment
        texts = df_clean["_cleaned_text"].tolist()
        results = sentiment_service.predict_batch(texts)
        
        # Compute dashboard
        dashboard = compute_dashboard_metrics(df_clean, cols, results)
        
        # Attach predictions for export
        df_export = df_clean.drop(columns=["_cleaned_text", "_temp_num", "_parsed_date", "_period", "_normalized_actual"], errors="ignore").copy()
        df_export["predicted_sentiment"] = [r["sentiment"] for r in results]
        df_export["confidence"] = [r["confidence"] for r in results]
        
        session_id = "sample"
        session_store[session_id] = {
            "df_export": df_export,
            "filename": "product_reviews_and_sale.csv"
        }
        
        return {
            "session_id": session_id,
            "filename": "product_reviews_and_sale.csv",
            "detected_columns": cols,
            "cleaning_summary": cleaning_summary,
            "dashboard": dashboard
        }
    except Exception as e:
        logger.exception("Error loading sample dataset")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload custom CSV or Excel file, auto-detect columns and return preview."""
    try:
        content = await file.read()
        filename = file.filename or "uploaded_data.csv"
        
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            # Try comma, semicolon, tab
            try:
                df = pd.read_csv(io.BytesIO(content))
            except Exception:
                df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
                
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file contains no data.")
            
        upload_id = str(uuid.uuid4())
        cols = detect_columns(df)
        
        # Store uploaded dataframe in session
        session_store[upload_id] = {
            "df_raw": df,
            "filename": filename,
            "detected_columns": cols
        }
        
        # Preview rows (clean NaN for JSON serialization)
        preview_df = df.head(5).copy()
        preview_data = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")
        
        return {
            "upload_id": upload_id,
            "filename": filename,
            "total_rows": len(df),
            "columns": list(df.columns),
            "detected_columns": cols,
            "preview": preview_data
        }
    except Exception as e:
        logger.exception("Error processing uploaded file")
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")

@app.post("/api/analyze")
def analyze_dataset(req: AnalyzeRequest):
    """Run sentiment analysis on uploaded file using confirmed/custom column mapping."""
    try:
        session = session_store.get(req.upload_id)
        if not session or "df_raw" not in session:
            raise HTTPException(status_code=404, detail="Upload session expired or invalid. Please re-upload.")
            
        df = session["df_raw"]
        cols = req.column_mapping
        text_col = cols.get("text_column")
        if not text_col or text_col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Review text column '{text_col}' not found in dataset.")
            
        df_clean, cleaning_summary = clean_dataset(df, text_col)
        
        texts = df_clean["_cleaned_text"].tolist()
        results = sentiment_service.predict_batch(texts)
        
        dashboard = compute_dashboard_metrics(df_clean, cols, results)
        
        # Prepare export DF
        df_export = df_clean.drop(columns=["_cleaned_text", "_temp_num", "_parsed_date", "_period", "_normalized_actual"], errors="ignore").copy()
        df_export["predicted_sentiment"] = [r["sentiment"] for r in results]
        df_export["confidence"] = [r["confidence"] for r in results]
        
        session["df_export"] = df_export
        session["dashboard"] = dashboard
        session["cleaning_summary"] = cleaning_summary
        
        return {
            "session_id": req.upload_id,
            "filename": session.get("filename", "dataset.csv"),
            "detected_columns": cols,
            "cleaning_summary": cleaning_summary,
            "dashboard": dashboard
        }
    except Exception as e:
        logger.exception("Error during analysis")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict_single")
def predict_single_review(req: PredictSingleRequest):
    """Instantly classifies a single review string with sentiment and confidence score."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty.")
    res = sentiment_service.predict_single(req.text)
    return {
        "text": req.text,
        "sentiment": res["sentiment"],
        "confidence": res["confidence"],
        "scores": res["scores"]
    }

@app.get("/api/export_csv")
def export_analyzed_csv(session_id: str):
    """Download the analyzed dataset as CSV with original columns plus predicted sentiment and confidence."""
    session = session_store.get(session_id)
    if not session or "df_export" not in session:
        raise HTTPException(status_code=404, detail="Session data not found for export.")
        
    df_export: pd.DataFrame = session["df_export"]
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    orig_name = session.get("filename", "reviews.csv")
    base_name = os.path.splitext(orig_name)[0]
    export_filename = f"{base_name}_reviewsense_analyzed.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={export_filename}"}
    )

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
