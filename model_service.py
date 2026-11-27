"""
Sentiment Analysis Model Service for ReviewSense
Model: cardiffnlp/twitter-xlm-roberta-base-sentiment (positive / neutral / negative)
Optimizations:
- Unique text deduplication and mapping back
- In-memory and disk persistent caching
- Batch inference
- Graceful offline fallback if Hugging Face model download is delayed or unavailable
"""
import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReviewSenseModel")

MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

# Lexicon for fast fallback if offline/HF unreachable
POSITIVE_WORDS = {
    "excellent", "good", "great", "awesome", "amazing", "love", "best", "superb",
    "fantastic", "outstanding", "perfect", "worth", "durable", "comfortable",
    "crisp", "punchy", "vivid", "soft", "genuine", "sturdy", "smooth", "happy",
    "liked", "exceeded", "vibrant", "radiant", "loved", "satisfied", "pleased"
}
NEGATIVE_WORDS = {
    "bad", "terrible", "horrible", "worst", "poor", "waste", "cheap", "broken",
    "defective", "disappointed", "disappointing", "stopped", "drainage", "fake",
    "duplicate", "counterfeit", "leaks", "cracked", "hazard", "slow", "delayed",
    "shrunk", "inaccurate", "detached", "peeling", "rash", "crushed", "hate", "fails"
}
NEUTRAL_WORDS = {
    "okay", "average", "mediocre", "decent", "acceptable", "moderate", "normal",
    "fine", "standard", "ordinary", "fair"
}

class SentimentModelService:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.pipeline = None
        self.is_loaded = False
        self.load_error = None
        # Cache for unique texts -> result
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_disk_cache()

    def _get_cache_path(self) -> str:
        cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "sentiment_cache.json")

    def _load_disk_cache(self):
        try:
            path = self._get_cache_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached sentiment results from disk.")
        except Exception as e:
            logger.warning(f"Could not load disk cache: {e}")

    def _save_disk_cache(self):
        try:
            path = self._get_cache_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not save disk cache: {e}")

    def load_model(self):
        """Loads the Hugging Face transformer model pipeline."""
        if self.is_loaded or self.pipeline is not None:
            return True
        try:
            from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
            logger.info(f"Loading Hugging Face model: {self.model_name}...")
            # Use top_k=None to get probabilities for all classes
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                tokenizer=self.model_name,
                top_k=None,
                truncation=True,
                max_length=256
            )
            self.is_loaded = True
            logger.info("Hugging Face model loaded successfully!")
            return True
        except Exception as e:
            self.load_error = str(e)
            logger.warning(f"Failed to load HF model {self.model_name}: {e}. Will use calibrated fallback analyzer.")
            return False

    def _fallback_predict(self, text: str) -> Dict[str, Any]:
        """Calibrated fallback rule/lexicon-based sentiment prediction."""
        if not text or not isinstance(text, str):
            return {"sentiment": "neutral", "confidence": 0.5, "scores": {"positive": 0.25, "neutral": 0.5, "negative": 0.25}}
        
        words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
        pos_hits = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_hits = sum(1 for w in words if w in NEGATIVE_WORDS)
        neu_hits = sum(1 for w in words if w in NEUTRAL_WORDS)
        
        # Check explicit negative patterns (e.g. not good, stopped working, waste of money)
        t_low = text.lower()
        if any(p in t_low for p in ["not good", "never buy", "waste of money", "don't buy", "stopped working", "stopped turning"]):
            neg_hits += 2
        if any(p in t_low for p in ["worth every penny", "must buy", "highly recommend", "value for money", "exceeded my expectations"]):
            pos_hits += 2

        score_diff = pos_hits - neg_hits
        if score_diff > 0:
            sentiment = "positive"
            conf = min(0.98, 0.65 + 0.1 * min(score_diff, 3))
            scores = {"positive": conf, "neutral": round((1-conf)*0.7, 3), "negative": round((1-conf)*0.3, 3)}
        elif score_diff < 0:
            sentiment = "negative"
            conf = min(0.98, 0.65 + 0.1 * min(abs(score_diff), 3))
            scores = {"positive": round((1-conf)*0.3, 3), "neutral": round((1-conf)*0.7, 3), "negative": conf}
        else:
            if neu_hits > 0 or "average" in t_low or "okay" in t_low or "decent" in t_low:
                sentiment = "neutral"
                conf = 0.75
            else:
                sentiment = "neutral"
                conf = 0.55
            scores = {"positive": 0.22, "neutral": conf, "negative": round(1 - 0.22 - conf, 3)}
            
        return {
            "sentiment": sentiment,
            "confidence": round(conf, 3),
            "scores": scores
        }

    def predict_single(self, text: str) -> Dict[str, Any]:
        """Predict sentiment for a single review."""
        cleaned = text.strip() if isinstance(text, str) else ""
        if cleaned in self.cache:
            return self.cache[cleaned]
            
        if self.load_model() and self.pipeline:
            try:
                # pipeline output is a list of dicts [{'label': 'positive', 'score': 0.9}, ...]
                outputs = self.pipeline(cleaned[:512])
                # Normalize label format
                scores = {}
                for item in outputs[0]:
                    lbl = item["label"].lower()
                    if "pos" in lbl:
                        scores["positive"] = round(float(item["score"]), 4)
                    elif "neg" in lbl:
                        scores["negative"] = round(float(item["score"]), 4)
                    else:
                        scores["neutral"] = round(float(item["score"]), 4)
                
                # ensure all three exist
                for k in ["positive", "neutral", "negative"]:
                    if k not in scores:
                        scores[k] = 0.0
                        
                best_label = max(scores, key=scores.get)
                res = {
                    "sentiment": best_label,
                    "confidence": round(scores[best_label], 4),
                    "scores": scores
                }
                self.cache[cleaned] = res
                return res
            except Exception as e:
                logger.warning(f"Error predicting with HF model: {e}")
                
        # Fallback
        res = self._fallback_predict(cleaned)
        self.cache[cleaned] = res
        return res

    def predict_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
        """
        Run the model ONCE per unique review text and map results back to all rows.
        This optimizes datasets with repeated reviews!
        """
        # Step 1: Find unique texts
        unique_texts = list(set(t.strip() if isinstance(t, str) else "" for t in texts))
        
        # Step 2: Separate cached vs uncached
        uncached = [t for t in unique_texts if t not in self.cache and len(t) > 0]
        
        # Try loading HF model
        model_ready = self.load_model()
        
        if uncached:
            logger.info(f"Predicting sentiment for {len(uncached)} unique reviews (total rows: {len(texts)})...")
            if model_ready and self.pipeline:
                try:
                    for i in range(0, len(uncached), batch_size):
                        batch = uncached[i:i+batch_size]
                        # truncate if overly long
                        truncated_batch = [t[:512] for t in batch]
                        batch_outputs = self.pipeline(truncated_batch)
                        for text_orig, outputs in zip(batch, batch_outputs):
                            scores = {}
                            for item in outputs:
                                lbl = item["label"].lower()
                                if "pos" in lbl:
                                    scores["positive"] = round(float(item["score"]), 4)
                                elif "neg" in lbl:
                                    scores["negative"] = round(float(item["score"]), 4)
                                else:
                                    scores["neutral"] = round(float(item["score"]), 4)
                            for k in ["positive", "neutral", "negative"]:
                                if k not in scores:
                                    scores[k] = 0.0
                            best_label = max(scores, key=scores.get)
                            self.cache[text_orig] = {
                                "sentiment": best_label,
                                "confidence": round(scores[best_label], 4),
                                "scores": scores
                            }
                except Exception as e:
                    logger.warning(f"Batch HF prediction failed, falling back: {e}")
                    for t in uncached:
                        if t not in self.cache:
                            self.cache[t] = self._fallback_predict(t)
            else:
                for t in uncached:
                    self.cache[t] = self._fallback_predict(t)
                    
            # Save updated cache to disk
            self._save_disk_cache()

        # Step 3: Map results back to all rows
        results = []
        for t in texts:
            cleaned = t.strip() if isinstance(t, str) else ""
            if cleaned in self.cache:
                results.append(self.cache[cleaned])
            else:
                results.append(self._fallback_predict(cleaned))
                
        return results

# Singleton instance
sentiment_service = SentimentModelService()
