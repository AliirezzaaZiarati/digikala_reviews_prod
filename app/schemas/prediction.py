from pydantic import BaseModel, Field

MAX_TEXT_LENGTH = 5000  # سقف طول متن؛ در README مستند می‌کنیم


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)
    model_id: str = Field(..., description="شناسه‌ی مدل، مثل tfidf_baseline")


class HeadResult(BaseModel):
    label: str
    probabilities: dict[str, float]


class PredictResponse(BaseModel):
    model_id: str
    model_name: str
    normalizer_version: str
    recommendation: HeadResult
    rating_band: HeadResult
    latency_ms: float


class NormalizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)


class NormalizeResponse(BaseModel):
    original: str
    normalized: str | None
    normalizer_version: str