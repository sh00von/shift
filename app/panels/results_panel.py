"""Bottom/right panel — summary stats table + per-transect detail plot."""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QPushButton,
)


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._series  = None
        self._results = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # ── Summary table ─────────────────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Summary (per transect)"))
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["T-ID", "EPR", "LRR", "BP rate", "BP break yr",
             "Bayes rate", "Bayes break yr", "N breaks", "RF RMSE"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        ll.addWidget(self.table)
        splitter.addWidget(left)

        # ── Transect detail plot ──────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Transect ID:"))
        self.tid_spin = QSpinBox()
        self.tid_spin.setRange(0, 9999)
        ctrl.addWidget(self.tid_spin)
        go_btn = QPushButton("Plot")
        go_btn.clicked.connect(self._plot_transect)
        ctrl.addWidget(go_btn)
        ctrl.addStretch()
        rl.addLayout(ctrl)

        self.fig = Figure(figsize=(6, 4), tight_layout=True)
        self.ax  = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        rl.addWidget(self.canvas)
        splitter.addWidget(right)

        splitter.setSizes([400, 500])
        root.addWidget(splitter)

        # ── Aggregate stats bar ───────────────────────────────────────────
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-family:monospace; padding:4px;")
        root.addWidget(self.stats_label)

    def load_results(self, series_list, results):
        self._series  = series_list
        self._results = results
        self._populate_table()
        self._show_aggregate_stats()

    def _populate_table(self):
        classic   = self._results.get("classic", [])
        breakpt   = self._results.get("breakpoint", [])
        bayesian  = self._results.get("bayesian", [])
        rf_res    = self._results.get("rf", [])

        n = len(self._series)
        self.table.setRowCount(n)
        self.tid_spin.setMaximum(max(s.transect_id for s in self._series))

        for i, s in enumerate(self._series):
            cl  = classic[i]  if i < len(classic)  else None
            bp  = breakpt[i]  if i < len(breakpt)  else None
            bay = bayesian[i] if i < len(bayesian)  else None
            rf  = rf_res[i]   if i < len(rf_res)   else None

            def cell(v, fmt=".1f"):
                txt = f"{v:{fmt}}" if v is not None else "—"
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignCenter)
                return item

            self.table.setItem(i, 0, cell(s.transect_id, "d"))
            self.table.setItem(i, 1, cell(cl.epr if cl else None))
            self.table.setItem(i, 2, cell(cl.lrr if cl else None))
            self.table.setItem(i, 3, cell(bp.overall_rate if bp else None))
            self.table.setItem(i, 4, cell(
                bp.breakpoints[-1].year if bp and bp.breakpoints else None, ".0f"
            ))
            self.table.setItem(i, 5, cell(bay.overall_rate if bay else None))
            self.table.setItem(i, 6, cell(
                bay.breakpoints[0].year if bay and bay.breakpoints else None, ".0f"
            ))
            self.table.setItem(i, 7, cell(len(bp.breakpoints) if bp else None, "d"))
            self.table.setItem(i, 8, cell(rf.rf_rmse if rf else None))

    def _show_aggregate_stats(self):
        classic = self._results.get("classic", [])
        breakpt = self._results.get("breakpoint", [])
        eprs = [r.epr for r in classic if r.epr is not None]
        pbr  = [r.overall_rate for r in breakpt if r.overall_rate is not None]
        n_brk = sum(1 for r in breakpt if r.breakpoints)
        n = len(self._series)
        self.stats_label.setText(
            f"  Transects: {n}  |  "
            f"EPR mean: {np.mean(eprs):.1f} m/yr  |  "
            f"Post-break mean: {np.mean(pbr):.1f} m/yr  |  "
            f"Transects with break: {n_brk} ({100*n_brk/n:.0f}%)  |  "
            f"Erosional (EPR): {sum(1 for e in eprs if e<0)} ({100*sum(1 for e in eprs if e<0)/len(eprs):.0f}%)"
        )

    def _on_row_selected(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = self.table.currentRow()
        tid_item = self.table.item(row, 0)
        if tid_item:
            self.tid_spin.setValue(int(tid_item.text()))
            self._plot_transect()

    def _plot_transect(self):
        if not self._series:
            return
        tid = self.tid_spin.value()
        series_map = {s.transect_id: s for s in self._series}
        s = series_map.get(tid)
        if s is None:
            return

        bp_results  = self._results.get("breakpoint", [])
        bp_map      = {r.transect_id: r for r in bp_results}
        bay_results = self._results.get("bayesian", [])
        bay_map     = {r.transect_id: r for r in bay_results}
        fc_results  = self._results.get("forecast", [])
        fc_map      = {r.transect_id: r for r in fc_results}

        r_bp  = bp_map.get(tid)
        r_bay = bay_map.get(tid)
        r_fc  = fc_map.get(tid)

        self.ax.clear()
        years = s.years()
        d     = s.distances

        self.ax.scatter(years, d, color="steelblue", zorder=5, s=40, label="Observed")
        self.ax.plot(years, d, color="steelblue", alpha=0.4)

        # LRR line
        cl_results = self._results.get("classic", [])
        cl_map = {r.transect_id: r for r in cl_results}
        cl = cl_map.get(tid)
        if cl and cl.lrr is not None:
            y0 = years[0]
            lrr_line = [cl.lrr*(y-y0)+d[0] for y in years]
            self.ax.plot(years, lrr_line, "k--", alpha=0.6,
                         label=f"LRR {cl.lrr:.1f} m/yr")

        # Breakpoints
        colors = ["#e63946","#f4a261","#2a9d8f","#457b9d"]
        if r_bp:
            for i, bp in enumerate(r_bp.breakpoints):
                c = colors[i % len(colors)]
                self.ax.axvline(bp.year, color=c, linestyle=":", linewidth=1.5)
                self.ax.annotate(
                    f"{bp.year:.0f}\n{bp.rate_before:.0f}→{bp.rate_after:.0f}",
                    xy=(bp.year, np.mean(d)), fontsize=7.5, color=c,
                    ha="left", va="center",
                    xytext=(4, 0), textcoords="offset points",
                )

        # Bayesian breakpoint (purple dashed)
        if r_bay and r_bay.breakpoints:
            for bp in r_bay.breakpoints:
                self.ax.axvline(
                    bp.year, color="#7c3aed", linestyle="-.", linewidth=1.2,
                    label=f"Bayes break {bp.year:.0f} ({bp.rate_before:.0f}→{bp.rate_after:.0f})"
                )

        # Forecast
        if r_fc and r_fc.forecast_years:
            fy = r_fc.forecast_years
            fd = r_fc.forecast_distances
            self.ax.plot(fy, fd, "r-", linewidth=1.5, label="Forecast")
            self.ax.fill_between(fy, r_fc.forecast_lower, r_fc.forecast_upper,
                                 color="red", alpha=0.12, label="90% CI")

        self.ax.set_xlabel("Year")
        self.ax.set_ylabel("Distance from baseline (m)")
        self.ax.set_title(f"Transect {tid}")
        self.ax.legend(fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw()
