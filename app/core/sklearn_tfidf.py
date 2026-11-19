import os

import joblib

from app.core.base import BaseModel


class SklearnTfidfModel(BaseModel):
    def load(self) -> None:
        root = self.models_root
        self.vectorizer = joblib.load(os.path.join(root, self.cfg["vectorizer"]))
        self.heads = {}
        for head_name, head_cfg in self.cfg["heads"].items():
            clf = joblib.load(os.path.join(root, head_cfg["file"]))
            # کلید YAML ممکن است عدد باشد؛ برای اطمینان به int تبدیل می‌کنیم
            labels = {int(k): v for k, v in head_cfg["labels"].items()}
            self.heads[head_name] = (clf, labels)

    def predict(self, text: str) -> dict:
        X = self.vectorizer.transform([text])  # یک متن -> ماتریس ویژگی
        result = {}
        for head_name, (clf, labels) in self.heads.items():
            probs = clf.predict_proba(X)[0]
            # clf.classes_ ترتیب واقعی ستون‌های probs را می‌گوید
            by_label = {labels[int(c)]: float(p) for c, p in zip(clf.classes_, probs)}
            best = max(by_label, key=by_label.get)
            result[head_name] = {"label": best, "probabilities": by_label}
        return result