"""
Integration test for ReviewSense API endpoints
"""
import sys
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_app():
    print("Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200
    assert "ReviewSense" in r.text
    print("GET / passed!")

    print("Testing GET /api/sample ...")
    r = client.get("/api/sample")
    assert r.status_code == 200
    data = r.json()
    assert data["filename"] == "product_reviews_and_sale.csv"
    assert "dashboard" in data
    assert "summary_cards" in data["dashboard"]
    cards = data["dashboard"]["summary_cards"]
    print(f"Sample loaded: {cards['total_reviews']} reviews, {cards['pct_positive']}% positive, {cards['pct_negative']}% negative.")
    print("GET /api/sample passed!")

    print("Testing POST /api/predict_single ...")
    r = client.post("/api/predict_single", json={"text": "Outstanding sound and ultra-fast charging! Love it."})
    assert r.status_code == 200
    pred = r.json()
    print(f"Prediction: {pred['sentiment']} (Confidence: {pred['confidence']})")
    assert pred["sentiment"] == "positive"
    print("POST /api/predict_single passed!")

    print("Testing GET /api/export_csv?session_id=sample ...")
    r = client.get("/api/export_csv?session_id=sample")
    assert r.status_code == 200
    assert "predicted_sentiment" in r.text
    print("GET /api/export_csv passed!")

    print("\nALL INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_app()
