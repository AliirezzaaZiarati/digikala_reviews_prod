FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the code and config; model files are mounted at runtime
COPY app ./app
COPY models.yaml .

# Where the container will look for models (mounted via volume)
ENV MODELS_ROOT=/models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]