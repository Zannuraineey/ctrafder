"""
Automated Model Retraining Script.
Loads recent data, computes double-barrier labels, and registers updated models.
"""

from app.database import init_db
from app.learning.trainer import ModelTrainer
from main import generate_synthetic_candles

if __name__ == "__main__":
    init_db()
    print("Generating training dataset for XAUUSD...")
    candles = generate_synthetic_candles("XAUUSD", count=600)
    print("Training ML Models...")
    results = ModelTrainer.train_models_on_candles(candles)
    print("Results:", results)
