"""Centre panel — matplotlib map canvas showing transects coloured by rate."""
from __future__ import annotations

import numpy as np
import geopandas as gpd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.cm import RdYlGn
from matplotlib.colors import Normalize, TwoSlopeNorm
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QLabel


class MapPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._transects = None
        self._results   = None
        self._series    = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Toolbar row
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Colour by:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "EPR (m/yr)", "LRR (m/yr)", "Post-break rate (m/yr)",
            "Break year", "BIC gain vs LRR",
            "Bayesian break year", "Bayesian post-break rate (m/yr)",
        ])
        self.metric_combo.currentIndexChanged.connect(self._redraw)
        ctrl.addWidget(self.metric_combo)
        ctrl.addStretch()
        root.addLayout(ctrl)

        self.fig = Figure(figsize=(8, 6), tight_layout=True)
        self.ax  = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        root.addWidget(self.toolbar)
        root.addWidget(self.canvas)

    def show_transects_only(self, transects):
        """Draw raw transects on map before analysis is run."""
        self.ax.clear()
        transects.plot(ax=self.ax, color="#2563eb", linewidth=0.8, alpha=0.7)
        self.ax.set_title(f"{len(transects)} transects — preview", fontsize=11)
        self.ax.set_xlabel("Easting (m)")
        self.ax.set_ylabel("Northing (m)")
        self.ax.ticklabel_format(style="sci", axis="both", scilimits=(0, 0))
        self.canvas.draw()

    def load_results(self, series_list, results, transects):
        self._series    = series_list
        self._results   = results
        self._transects = transects
        self._redraw()

    def _redraw(self):
        if self._transects is None:
            return
        self.ax.clear()
        metric = self.metric_combo.currentText()
        values = self._get_values(metric)
        if values is None:
            return

        vals = np.array(values, dtype=float)
        valid = ~np.isnan(vals)

        # Build per-transect GDF with values
        gdf = self._transects.copy()
        tid_to_val = {tid: v for tid, v in zip(
            [s.transect_id for s in self._series], vals
        )}
        gdf["value"] = gdf["transect_id"].map(tid_to_val)
        gdf = gdf.dropna(subset=["value"])

        vmin, vmax = np.nanpercentile(vals[valid], 5), np.nanpercentile(vals[valid], 95)

        if "rate" in metric.lower() or "EPR" in metric or "LRR" in metric:
            norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
            cmap = "RdYlGn"
        else:
            norm = Normalize(vmin=vmin, vmax=vmax)
            cmap = "plasma"

        gdf.plot(column="value", ax=self.ax, cmap=cmap, norm=norm,
                 linewidth=1.5, legend=True,
                 legend_kwds={"label": metric, "shrink": 0.6})

        self.ax.set_title(f"SHIFT — {metric}", fontsize=11)
        self.ax.set_xlabel("Easting (m)")
        self.ax.set_ylabel("Northing (m)")
        self.ax.ticklabel_format(style="sci", axis="both", scilimits=(0, 0))
        self.canvas.draw()

    def _get_values(self, metric: str) -> list | None:
        from shift.stats.classic import _ols
        from scipy import stats as st
        import numpy as np

        series = self._series
        results = self._results

        if "EPR" in metric:
            return [r.epr for r in results.get("classic", [])]
        elif "LRR" in metric:
            return [r.lrr for r in results.get("classic", [])]
        elif "Post-break" in metric:
            return [r.overall_rate for r in results.get("breakpoint", [])]
        elif "Break year" in metric:
            out = []
            for r in results.get("breakpoint", []):
                if r.breakpoints:
                    out.append(r.breakpoints[-1].year)
                else:
                    out.append(float("nan"))
            return out
        elif "Bayesian break year" in metric:
            out = []
            for r in results.get("bayesian", []):
                if r and r.breakpoints:
                    out.append(r.breakpoints[0].year)
                else:
                    out.append(float("nan"))
            return out
        elif "Bayesian post-break" in metric:
            return [r.overall_rate if r else None
                    for r in results.get("bayesian", [])]
        elif "BIC" in metric:
            out = []
            for s, r_bp in zip(series, results.get("breakpoint", [])):
                years = np.array(s.years())
                d     = np.array(s.distances)
                n     = len(years)
                res   = st.linregress(years, d)
                sse_l = np.sum((d - (res.slope*years+res.intercept))**2)
                b_lin = n * np.log(max(sse_l/n, 1e-10)) + 2*np.log(n)
                bp_idx = [int(np.argmin(np.abs(years - bp.year)))
                          for bp in r_bp.breakpoints]
                if bp_idx:
                    cuts = [0]+sorted(bp_idx)+[n]
                    sse_b = sum(
                        np.sum((d[cuts[i]:cuts[i+1]] -
                                (st.linregress(years[cuts[i]:cuts[i+1]],
                                               d[cuts[i]:cuts[i+1]]).slope *
                                 years[cuts[i]:cuts[i+1]] +
                                 st.linregress(years[cuts[i]:cuts[i+1]],
                                               d[cuts[i]:cuts[i+1]]).intercept))**2)
                        for i in range(len(cuts)-1)
                        if cuts[i+1]-cuts[i] >= 2
                    )
                    k = 2*(len(cuts)-1)+len(bp_idx)
                    b_bp = n*np.log(max(sse_b/n,1e-10)) + k*np.log(n)
                    out.append(b_lin - b_bp)
                else:
                    out.append(0.0)
            return out
        return None
