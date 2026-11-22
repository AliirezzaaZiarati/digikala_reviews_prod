# Digikala Review Service

> **Part of the main project:** [digikala-review-transformer](https://github.com/AliirezzaaZiarati/digikala-review-transformer).
> This repository contains only the **serving layer** (API, web UI, Docker) for the models trained there.

A small service that classifies Persian Digikala reviews. For one review text it returns:

- **Recommendation:** `recommended`, `not_recommended` or `no_idea`
- **Rating band:** `low`, `medium` or `high`

Each answer comes with the probability of every class.

## How it works

```text
Browser ──► Streamlit UI (:8501) ──► FastAPI (:8000) ──► normalizer ──► model registry ──► model
```

- Models are listed in `models.yaml` and loaded once at startup.
- Every model follows one contract (`load()` and `predict()`), so new models need no code changes in the API or the UI.
- Model files are never copied into the image. They are mounted read-only.

## Quick start

Both repositories are expected side by side, with the trained artifacts in the training repository:

```text
projects/
├── digikala-review-transformer/     # training repo (artifacts/ inside)
└── digikala_reviews_prod/           # this repo
```

**1. Prepare the wheels (once).** The image installs packages offline from a local `wheels/` folder, which is not stored in git:

```bash
mkdir -p wheels
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD":/work -w /work python:3.12-slim \
  pip download -r requirements.txt -d wheels
```

**2. Build and run:**

```bash
docker compose up --build
```

| Service | Address |
| --- | --- |
| Web UI | <http://localhost:8501> |
| API docs | <http://localhost:8000/docs> |
| Readiness | <http://localhost:8000/ready> |

**Without Docker** (Python 3.12):

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
MODELS_ROOT=../digikala-review-transformer/artifacts uvicorn app.main:app
streamlit run ui/app.py
```

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service is alive |
| `GET` | `/ready` | Models loaded, with errors per model |
| `GET` | `/models` | Available models |
| `POST` | `/normalize` | Persian text normalization |
| `POST` | `/predict` | Prediction with the chosen model |

Request body of `/predict`: `{"text": "...", "model_id": "tfidf_baseline"}`.
Errors: `400` unknown model, `422` invalid text, `503` models not ready.

## Layout

```text
app/                  FastAPI service (core/, schemas/, main.py)
ui/                   Streamlit page
models.yaml           Model registry: the one file to edit when adding a model
Dockerfile            API image
Dockerfile.ui         UI image
docker-compose.yml    Both services, ports and the model volume
requirements.txt      Pinned to the training environment
```

## Status

| Component | State |
| --- | --- |
| TF-IDF + Logistic Regression (both heads) | Served |
| Fine-tuned Transformer encoders (GPU) | Planned |
| Automated API tests | Planned |

## More

Detailed documentation lives in the main project's Notion workspace, on the page for this phase.
