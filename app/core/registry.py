import os

import yaml

from app.core.base import BaseModel
from app.core.sklearn_tfidf import SklearnTfidfModel

# جدول نوع -> کلاس. انکودرها بعداً اینجا یک خط اضافه می‌کنند.
MODEL_TYPES: dict[str, type[BaseModel]] = {
    "sklearn_tfidf": SklearnTfidfModel,
}

# مسیرها از متغیر محیطی خوانده می‌شوند تا هم روی سیستم و هم در داکر کار کنند
MODELS_ROOT = os.environ.get("MODELS_ROOT", "artifacts")
CONFIG_PATH = os.environ.get("MODELS_CONFIG", "models.yaml")


class ModelRegistry:
    def __init__(self, config_path: str = CONFIG_PATH, models_root: str = MODELS_ROOT):
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.models_root = models_root
        self.models: dict[str, BaseModel] = {}
        self.errors: dict[str, str] = {}

    def load_all(self) -> None:
        """همه‌ی مدل‌های فعال را load می‌کند. خرابی یک مدل بقیه را نمی‌خواباند."""
        for model_id, cfg in self.config["models"].items():
            if not cfg.get("enabled", True):
                continue
            cls = MODEL_TYPES.get(cfg["type"])
            if cls is None:
                self.errors[model_id] = f"unknown type: {cfg['type']}"
                continue
            try:
                model = cls(model_id, cfg, self.models_root)
                model.load()
                self.models[model_id] = model
            except Exception as e:  # noqa: BLE001
                self.errors[model_id] = f"{type(e).__name__}: {e}"

    def get(self, model_id: str) -> BaseModel | None:
        return self.models.get(model_id)

    def list_models(self) -> list[dict]:
        return [{"id": mid, "name": m.display_name} for mid, m in self.models.items()]