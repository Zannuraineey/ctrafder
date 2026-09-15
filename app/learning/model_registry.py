"""
Model Registry: Model Versioning and Deployment Pipeline.
Section 85 of project.md.
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from app.database.session import get_db_session
from app.database.models import ModelRegistryModel
from app.ai.models.base import BaseMLModel


class ModelRegistry:
    """
    Manages versioned model artifacts across staging, production, and archive.
    """

    BASE_DIR = "models"

    @classmethod
    def save_model(
        cls,
        model: BaseMLModel,
        stage: str = "production",
        metrics: Optional[Dict[str, float]] = None,
    ) -> str:
        metrics = metrics or {}
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version = f"{model.version}_{timestamp_str}"

        dir_path = os.path.join(cls.BASE_DIR, stage, model.name)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"{version}.pkl")

        # Save model binary
        model.save(file_path)

        # Save metadata JSON
        meta_path = os.path.join(dir_path, f"{version}_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(
                {
                    "model_name": model.name,
                    "version": version,
                    "stage": stage,
                    "created_at": datetime.utcnow().isoformat(),
                    "metrics": metrics,
                    "features": model.feature_names,
                },
                f,
                indent=2,
            )

        # Record in database
        try:
            with get_db_session() as session:
                record = ModelRegistryModel(
                    model_name=model.name,
                    version=version,
                    stage=stage,
                    file_path=file_path,
                    accuracy=metrics.get("accuracy"),
                    profit_factor=metrics.get("profit_factor"),
                    win_rate=metrics.get("win_rate"),
                    sharpe=metrics.get("sharpe"),
                    metrics_json=json.dumps(metrics),
                )
                session.merge(record)
        except Exception as e:
            logger.error(f"Failed to record model in registry database: {e}")

        logger.info(f"Model {model.name} [{version}] registered in '{stage}'.")
        return file_path
