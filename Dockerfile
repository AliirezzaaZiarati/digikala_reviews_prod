FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# Install offline from the local wheels folder (mounted only during this step,
# so the 3 GB of wheels do not end up inside the image layer)
RUN --mount=type=bind,source=wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copy only the code and config; model files are mounted at runtime
COPY app ./app
COPY models.yaml .

# Where the container will look for models (mounted via volume)
ENV MODELS_ROOT=/models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]