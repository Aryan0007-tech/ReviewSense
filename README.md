# ReviewSense — E-Commerce Sentiment Intelligence

ReviewSense is a clean, modern, and high-performance web application designed for analyzing customer sentiment in e-commerce product reviews.

## Key Features

1. **Dual Data Modes**:
   - Built-in sample dataset (`product_reviews_and_sale.csv`, 1,000 real reviews across Amazon, Flipkart, and Myntra). The app opens pre-analyzed so the dashboard is immediately populated.
   - Drag & Drop upload for any custom `.csv` or `.xlsx` files with arbitrary schemas and column names.
2. **Automatic Column Detection**:
   - Automatically identifies: Review Text (longest average text), Sentiment Label, Star Ratings, Categorical Segments (Platform, Category, Brand), Numeric Metrics (Price, Sales), and Timestamps.
   - Auto-derives product categories from keywords in review text if no category column exists.
   - Interactive "Detected Columns" panel allows users to review and modify mappings before running analysis.
3. **Optimized AI Sentiment Engine**:
   - Powered by Hugging Face `cardiffnlp/twitter-xlm-roberta-base-sentiment` (positive / neutral / negative).
   - Unique-text deduplication: runs inference once per distinct review and maps results back to all rows, drastically accelerating repeated review processing.
   - In-memory & disk persistent caching.
4. **Interactive Dashboard**:
   - Top summary cards: Total reviews, % positive, % neutral, % negative, average star rating.
   - 10 dynamic charts with plain-English takeaway captions:
     1. Overall Sentiment Distribution (Donut)
     2. Sentiment breakdown by Platform / Channel (Stacked Bar)
     3. Sentiment breakdown by Category (Stacked Bar)
     4. Customer Rating Distribution (Bar)
     5. Sentiment Trajectory Over Time (Line)
     6. Category Performance Leaders: Top positive & top negative volume (Horizontal Bar)
     7. Friction Matrix: Heatmap of negative reviews (Category vs Platform)
     8. Confusion Matrix & Model Accuracy heatmap (Predicted vs Actual labels)
     9. Voice of Customer: Top 10 Praises and Top 10 Complaints
     10. Economic Metrics vs Sentiment (e.g. Average Price per sentiment tier)
5. **AI Executive Insights**:
   - Synthesizes findings into a ~150-word plain-English executive summary using real data figures only: overall sentiment statement, top & bottom performers, 3 key praises, 3 key complaints, label alignment, and 3 seller recommendations.
6. **Try a Review (Live Inference)**:
   - Interactive single-review tester with live sentiment classification and confidence distribution meter.
7. **Review Explorer Table**:
   - Full-dataset paginated review table with live search and multi-facet filtering (sentiment and categorical channel).
8. **Export Capabilities**:
   - Export enriched dataset as CSV (original columns + `predicted_sentiment` + `confidence`).
   - Export dashboard as high-resolution image / printable report.

---

## Project Structure

```
reviewsense/
├── data/
│   └── product_reviews_and_sale.csv   # Built-in 1,000-row sample dataset
├── static/
│   ├── index.html                     # Responsive single-page interface
│   ├── style.css                      # Modern minimalist styling & responsive layout
│   └── app.js                         # Dynamic Chart.js rendering & client state
├── .cache/                            # Sentiment cache directory
├── column_detector.py                 # Intelligent schema detector & category derivation
├── analysis_engine.py                 # Cleaning, metrics calculation & AI insights generator
├── model_service.py                   # CardiffNLP Hugging Face model wrapper & caching
├── generate_sample_data.py            # Generates realistic sample reviews
├── precompute_sample_cache.py         # Warm-up script for instant launch
├── main.py                            # FastAPI backend server
├── requirements.txt                   # Project dependencies
└── README.md                          # Documentation
```

---

## Quickstart Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python main.py
```
Or with Uvicorn directly:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open in Browser
Navigate to:
```
http://127.0.0.1:8000
```
ReviewSense will load immediately with the pre-analyzed sample dataset ready to explore.
