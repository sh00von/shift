FROM python:3.11-slim

WORKDIR /app

# System deps for geopandas/pyproj
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY pyproject.toml ./
COPY api/ ./api/
COPY shift/ ./shift/
COPY sample_data/ ./sample_data/

RUN pip install --no-cache-dir \
    geopandas \
    shapely \
    pyproj \
    numpy \
    scipy \
    statsmodels \
    pmdarima \
    matplotlib \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    && pip install --no-cache-dir -e .

EXPOSE 8437

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8437"]
