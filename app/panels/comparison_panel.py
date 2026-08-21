"""
Comparison panel — RMSE / MAE / Bias / BIC table and bar charts
showing LRR vs Breakpoint vs Bayesian vs Random Forest.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as st

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from shift.models import TransectSeries
from shift.stats.classic import _ols


class ComparisonPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(QLabel(
            "Hold-out backtest: fit on all dates except last → predict last date. "
            "Lower RMSE/MAE = better prediction accuracy."
        ))

        splitter = QSplitter(Qt.Vertical)

        # ── Metrics table ─────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Method", "RMSE (m)", "MAE (m)", "Bias (m)", "RMSE improvement vs LRR"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.table)

        # ── Bar charts ────────────────────────────────────────────────────
        self.fig = Figure(figsize=(10, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.fig)
        splitter.addWidget(self.canvas)
        splitter.setSizes([200, 350])
        root.addWidget(splitter)

        # ── BIC summary ───────────────────────────────────────────────────
        self.bic_label = QLabel("")
        self.bic_label.setStyleSheet(
            "background:#f0f9ff; border:1px solid #bae6fd; "
            "padding:8px; border-radius:4px; font-family:monospace;"
        )
        self.bic_label.setWordWrap(True)
        root.addWidget(self.bic_label)

    def load_results(self, series_list: list, results: dict):
        metrics = self._compute_metrics(series_list, results)
        self._populate_table(metrics)
        self._plot_bars(metrics)
        self._show_bic(series_list, results)

    # ── Computation ───────────────────────────────────────────────────────

    def _compute_metrics(self, series_list, results) -> dict:
        """
        For each method, compute hold-out prediction errors:
        fit on series[:-1], predict series[-1].distance.
        """
        from sklearn.ensemble import RandomForestRegressor

        errors = {m: [] for m in ["lrr", "breakpoint", "bayesian", "rf"]}

        bp_map  = {r.transect_id: r for r in results.get("breakpoint", [])}
        bay_map = {r.transect_id: r for r in results.get("bayesian", [])}

        for s in series_list:
            if len(s) < 3:
                continue

            train = TransectSeries(
                transect_id=s.transect_id,
                dates=s.dates[:-1],
                distances=s.distances[:-1],
                uncertainties=s.uncertainties[:-1],
            )
            actual = s.distances[-1]
            actual_year = np.array(s.years())[-1]
            train_years = np.array(train.years())
            train_d     = np.array(train.distances)

            # LRR
            slope, _ = _ols(train_years, train_d)
            intercept = np.mean(train_d) - slope * np.mean(train_years)
            errors["lrr"].append(actual - (slope * actual_year + intercept))

            # Breakpoint — re-fit on training set
            from shift.stats.breakpoint import BreakpointMethod
            r_bp = BreakpointMethod().fit(train)
            if r_bp.breakpoints:
                rate = r_bp.breakpoints[-1].rate_after
                pred = train_d[-1] + rate * (actual_year - train_years[-1])
            else:
                pred = slope * actual_year + intercept
            errors["breakpoint"].append(actual - pred)

            # Bayesian (only if run)
            if results.get("bayesian"):
                r_bay = bay_map.get(s.transect_id)
                if r_bay and r_bay.breakpoints:
                    rate = r_bay.breakpoints[-1].rate_after
                    pred_b = train_d[-1] + rate * (actual_year - train_years[-1])
                else:
                    pred_b = slope * actual_year + intercept
                errors["bayesian"].append(actual - pred_b)

            # RF
            rf = RandomForestRegressor(n_estimators=200, random_state=42)
            rf.fit(train_years.reshape(-1, 1), train_d)
            pred_rf = float(rf.predict([[actual_year]])[0])
            errors["rf"].append(actual - pred_rf)

        out = {}
        lrr_rmse = None
        for method, errs in errors.items():
            if not errs:
                continue
            e = np.array(errs)
            rmse = float(np.sqrt(np.mean(e ** 2)))
            mae  = float(np.mean(np.abs(e)))
            bias = float(np.mean(e))
            out[method] = {"rmse": rmse, "mae": mae, "bias": bias, "n": len(e)}
            if method == "lrr":
                lrr_rmse = rmse

        # Add improvement % vs LRR
        if lrr_rmse:
            for m in out:
                out[m]["improvement"] = 100 * (1 - out[m]["rmse"] / lrr_rmse)

        return out

    def _populate_table(self, metrics: dict):
        labels = {
            "lrr":        "DSAS LRR (baseline)",
            "breakpoint": "SHIFT Breakpoint",
            "bayesian":   "SHIFT Bayesian",
            "rf":         "Random Forest",
        }
        order = ["lrr", "breakpoint", "bayesian", "rf"]
        rows  = [(k, metrics[k]) for k in order if k in metrics]

        self.table.setRowCount(len(rows))
        best_rmse = min(v["rmse"] for _, v in rows)

        for i, (method, m) in enumerate(rows):
            imp = f"{m['improvement']:+.1f}%" if method != "lrr" and "improvement" in m else "—"
            cells = [
                labels.get(method, method),
                f"{m['rmse']:.1f}",
                f"{m['mae']:.1f}",
                f"{m['bias']:+.1f}",
                imp,
            ]
            for j, txt in enumerate(cells):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                if method == "lrr":
                    item.setBackground(QColor("#fee2e2"))
                elif m["rmse"] == best_rmse:
                    item.setBackground(QColor("#dcfce7"))
                self.table.setItem(i, j, item)

    def _plot_bars(self, metrics: dict):
        self.fig.clear()
        if not metrics:
            return

        labels_map = {
            "lrr":        "LRR\n(DSAS)",
            "breakpoint": "Breakpoint\n(SHIFT)",
            "bayesian":   "Bayesian\n(SHIFT)",
            "rf":         "Random\nForest",
        }
        order  = [k for k in ["lrr", "breakpoint", "bayesian", "rf"] if k in metrics]
        labels = [labels_map[k] for k in order]
        colors = ["#ef4444", "#2563eb", "#7c3aed", "#f59e0b"]

        ax1 = self.fig.add_subplot(1, 3, 1)
        ax2 = self.fig.add_subplot(1, 3, 2)
        ax3 = self.fig.add_subplot(1, 3, 3)

        rmses = [metrics[k]["rmse"] for k in order]
        maes  = [metrics[k]["mae"]  for k in order]
        bias  = [metrics[k]["bias"] for k in order]

        bar_colors = [colors[i % len(colors)] for i in range(len(order))]

        ax1.bar(labels, rmses, color=bar_colors, edgecolor="white", linewidth=0.5)
        ax1.set_title("RMSE (m)", fontsize=10, fontweight="bold")
        ax1.set_ylabel("metres")
        for bar, v in zip(ax1.patches, rmses):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                     f"{v:.0f}", ha="center", va="bottom", fontsize=8)

        ax2.bar(labels, maes, color=bar_colors, edgecolor="white", linewidth=0.5)
        ax2.set_title("MAE (m)", fontsize=10, fontweight="bold")
        ax2.set_ylabel("metres")
        for bar, v in zip(ax2.patches, maes):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                     f"{v:.0f}", ha="center", va="bottom", fontsize=8)

        bar_cols_bias = ["#ef4444" if b > 0 else "#22c55e" for b in bias]
        ax3.bar(labels, bias, color=bar_cols_bias, edgecolor="white", linewidth=0.5)
        ax3.axhline(0, color="black", linewidth=0.8)
        ax3.set_title("Bias (m)  [+ = over-predict erosion]", fontsize=10, fontweight="bold")
        ax3.set_ylabel("metres")
        for bar, v in zip(ax3.patches, bias):
            ypos = v + 2 if v >= 0 else v - 10
            ax3.text(bar.get_x() + bar.get_width()/2, ypos,
                     f"{v:+.0f}", ha="center", va="bottom", fontsize=8)

        self.fig.tight_layout()
        self.canvas.draw()

    def _show_bic(self, series_list, results):
        bp_results = results.get("breakpoint", [])
        if not bp_results:
            return

        bic_diffs = []
        for s, r_bp in zip(series_list, bp_results):
            years = np.array(s.years())
            d     = np.array(s.distances)
            n     = len(years)
            res   = st.linregress(years, d)
            sse_l = np.sum((d - (res.slope * years + res.intercept)) ** 2)
            b_lin = n * np.log(max(sse_l / n, 1e-10)) + 2 * np.log(n)

            bp_idx = [int(np.argmin(np.abs(years - bp.year)))
                      for bp in r_bp.breakpoints]
            if bp_idx:
                cuts  = [0] + sorted(bp_idx) + [n]
                sse_b = 0.0
                for i in range(len(cuts) - 1):
                    sx, sy = years[cuts[i]:cuts[i+1]], d[cuts[i]:cuts[i+1]]
                    if len(sx) >= 2:
                        r2 = st.linregress(sx, sy)
                        sse_b += np.sum((sy - (r2.slope*sx + r2.intercept))**2)
                k    = 2 * (len(cuts) - 1) + len(bp_idx)
                b_bp = n * np.log(max(sse_b / n, 1e-10)) + k * np.log(n)
                bic_diffs.append(b_lin - b_bp)
            else:
                bic_diffs.append(0.0)

        bic_diffs = np.array(bic_diffs)
        n_strong  = int(np.sum(bic_diffs > 10))
        n_total   = len(bic_diffs)

        self.bic_label.setText(
            f"BIC Model Selection (Breakpoint vs Linear):   "
            f"Breakpoint wins: {np.sum(bic_diffs > 0)}/{n_total} transects   |   "
            f"Mean BIC gain: {np.mean(bic_diffs):.1f}   |   "
            f"Median BIC gain: {np.median(bic_diffs):.1f}   |   "
            f"Very strong evidence (ΔBIC > 10): {n_strong} transects "
            f"({100*n_strong/n_total:.1f}%)   "
            f"[ΔBIC > 10 = 'very strong' by Kass & Raftery 1995]"
        )
