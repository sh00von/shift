"""GeoJSON builder for the CBC (Coastal Behaviour Classification) layer."""
from __future__ import annotations

import shapely.geometry

from api.session import Session


def cbc_geojson(state: Session) -> dict:
    from shift.stats.cbc import LABEL_COLORS, LABELS

    if state.transects is None or not state.cbc_results:
        return {"geojson": {"type": "FeatureCollection", "features": []}, "legend": None}

    label_map = {r["transect_id"]: r for r in state.cbc_results}
    gdf = state.transects.to_crs("EPSG:4326")

    features = []
    counts: dict[str, int] = {lbl: 0 for lbl in LABELS}
    for _, row in gdf.iterrows():
        try:
            tid = int(row["transect_id"])
        except Exception:
            continue
        info = label_map.get(tid)
        label = info["label"] if info else "Stable"
        color = LABEL_COLORS.get(label, "#94a3b8")
        counts[label] = counts.get(label, 0) + 1
        features.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row["geometry"]),
            "properties": {"transect_id": tid, "label": label, "color": color},
        })

    legend = {
        "title": "Coastal Behaviour",
        "categories": [
            {"label": lbl, "color": LABEL_COLORS[lbl], "count": counts.get(lbl, 0)}
            for lbl in LABELS
            if counts.get(lbl, 0) > 0
        ],
    }
    return {"geojson": {"type": "FeatureCollection", "features": features}, "legend": legend}
