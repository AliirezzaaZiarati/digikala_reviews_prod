from abc import ABC, abstractmethod


class BaseModel(ABC):
    """قرارداد مشترک: هر مدل باید load و predict داشته باشد."""

    def __init__(self, model_id: str, cfg: dict, models_root: str):
        self.model_id = model_id
        self.cfg = cfg
        self.models_root = models_root
        self.display_name = cfg.get("display_name", model_id)

    @abstractmethod
    def load(self) -> None:
        """فایل‌های مدل را یک بار در حافظه بارگذاری می‌کند."""

    @abstractmethod
    def predict(self, text: str) -> dict:
        """متن نرمال‌شده را می‌گیرد و خروجی هر هد را برمی‌گرداند."""