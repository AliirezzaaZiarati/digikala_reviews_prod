import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.core.normalize import NORMALIZER_VERSION, normalize_text
from app.core.registry import ModelRegistry
from app.schemas.prediction import (
    NormalizeRequest,
    NormalizeResponse,
    PredictRequest,
    PredictResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = ModelRegistry()
    registry.load_all()
    app.state.registry = registry
    yield  # سرویس اینجا در حال کار است


app = FastAPI(title="Digikala Review API", lifespan=lifespan)


def _normalize(text: str) -> str:
    join = app.state.registry.config.get("normalizer", {}).get("join_suffixes", False)
    normalized = normalize_text(text, join_suffixes=join)
    if normalized is None:
        raise HTTPException(status_code=422, detail="The text is not valid (empty or just a URL).")
    return normalized


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    reg = app.state.registry
    if not reg.models:
        raise HTTPException(status_code=503, detail={"errors": reg.errors})
    return {"status": "ready", "loaded": list(reg.models), "errors": reg.errors}


@app.get("/models")
def models():
    return app.state.registry.list_models()


@app.post("/normalize", response_model=NormalizeResponse)
def normalize(req: NormalizeRequest):
    return NormalizeResponse(
        original=req.text,
        normalized=_normalize(req.text),
        normalizer_version=NORMALIZER_VERSION,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    model = app.state.registry.get(req.model_id)
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown Model: {req.model_id}")
    text = _normalize(req.text)
    start = time.perf_counter()
    result = model.predict(text)
    latency = (time.perf_counter() - start) * 1000
    return PredictResponse(
        model_id=req.model_id,
        model_name=model.display_name,
        normalizer_version=NORMALIZER_VERSION,
        latency_ms=round(latency, 2),
        **result,
    )