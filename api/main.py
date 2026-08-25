"""SHIFT FastAPI application — REST + WebSocket API wrapping the shift library.

Run with:  uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

warnings.filterwarnings("ignore")

from api.routers import exports, jobs, layers, session

app = FastAPI(title="SHIFT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(exports.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
