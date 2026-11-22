from abc import ABC, abstractmethod


class BaseModel(ABC):
    """Common contract: Every model must have `load` and `predict` methods."""

    def __init__(self, model_id: str, cfg: dict, models_root: str):
        self.model_id = model_id
        self.cfg = cfg
        self.models_root = models_root
        self.display_name = cfg.get("display_name", model_id)

    @abstractmethod
    def load(self) -> None:
        """It loads the model files into memory once."""

    @abstractmethod
    def predict(self, text: str) -> dict:
        """It takes the normalized text and returns the output of each head."""