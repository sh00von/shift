"""In-memory session store. Each browser session gets one Session holding
uploaded layers, pipeline outputs, and UI parameters — the server-side analogue
of the old NiceGUI per-page AppState."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    id: str

    # Raw uploaded data (temp file paths)
    shoreline_path: str | None = None
    baseline_path: str | None = None
    shoreline_filename: str = ""
    baseline_filename: str = ""

    # Column selections & date formatting
    date_col: str | None = None
    date_format: str = "auto"
    uncertainty_col: str | None = None
    default_uncertainty: float = 10.0

    # Transect parameters
    spacing: float = 250.0
    smoothing: float = 4000.0
    transect_length: float = 8000.0
    cast_side: str = "right"
    buffer_distance: float = 500.0

    # Method toggles
    run_classic: bool = True
    run_theilsen: bool = True
    run_ransac: bool = True
    run_breakpoint: bool = True
    run_rf: bool = True

    # Forecast parameters
    forecast_model: str = ""
    forecast_horizon: int = 10
    forecast_ci: float = 0.90

    # Map / styling
    style_metric: str = "LRR (m/yr)"
    color_ramp: str = "Red-Yellow-Green (DSAS)"
    shoreline_palette: str = "turbo"   # matplotlib colormap for date-coded shorelines

    # Pipeline outputs
    transects: Any = None            # GeoDataFrame
    series_list: list = field(default_factory=list)
    results: dict = field(default_factory=dict)

    # Bookkeeping
    logs: list[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)


class SessionStore:
    """Thread-unsafe-but-fine-for-single-worker registry of sessions."""

    def __init__(self, ttl_seconds: int = 60 * 60 * 6):
        self._sessions: dict[str, Session] = {}
        self._ttl = ttl_seconds

    def create(self) -> Session:
        sid = uuid.uuid4().hex
        s = Session(id=sid)
        self._sessions[sid] = s
        return s

    def get(self, sid: str) -> Session | None:
        s = self._sessions.get(sid)
        if s is not None:
            s.last_seen = time.time()
        return s

    def get_or_create(self, sid: str | None) -> Session:
        if sid and sid in self._sessions:
            return self.get(sid)  # type: ignore[return-value]
        return self.create()

    def sweep(self) -> None:
        now = time.time()
        stale = [k for k, v in self._sessions.items() if now - v.last_seen > self._ttl]
        for k in stale:
            self._sessions.pop(k, None)


store = SessionStore()
