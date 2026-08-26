FROM python:3.11-slim

WORKDIR /app

# System deps for geopandas / pyproj / shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 1: install heavy deps first so rebuilds are fast ──────────────────
# Copy only the manifest — source code changes won't bust this layer
COPY pyproject.toml ./
# Dummy package dir so pip install -e . resolves without the real source
RUN mkdir -p shift api && \
    pip install --no-cache-dir -e ".[dev]" && \
    rm -rf shift api

# ── Layer 2: copy source ─────────────────────────────────────────────────────
COPY shift/       ./shift/
COPY api/         ./api/
COPY sample_data/ ./sample_data/

# Re-install in editable mode without reinstalling deps (already cached above)
RUN pip install --no-cache-dir -e . --no-deps

EXPOSE 8437

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8437"]
