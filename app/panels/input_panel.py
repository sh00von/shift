"""Left panel — file inputs and analysis parameters."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class InputPanel(QWidget):
    run_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Files ──────────────────────────────────────────────────────────
        file_box = QGroupBox("Input Files")
        fl = QFormLayout(file_box)

        self.shoreline_edit = QLineEdit()
        self.shoreline_edit.setPlaceholderText("Select shoreline file…")
        sh_btn = QPushButton("Browse")
        sh_btn.clicked.connect(self._browse_shoreline)
        sh_row = QHBoxLayout()
        sh_row.addWidget(self.shoreline_edit)
        sh_row.addWidget(sh_btn)
        fl.addRow("Shoreline:", sh_row)

        self.baseline_edit = QLineEdit()
        self.baseline_edit.setPlaceholderText("Select baseline file…")
        bl_btn = QPushButton("Browse")
        bl_btn.clicked.connect(self._browse_baseline)
        bl_row = QHBoxLayout()
        bl_row.addWidget(self.baseline_edit)
        bl_row.addWidget(bl_btn)
        fl.addRow("Baseline:", bl_row)

        self.date_col_edit = QLineEdit("date")
        fl.addRow("Date column:", self.date_col_edit)

        self.uncertainty_col_edit = QLineEdit("uncertainty")
        fl.addRow("Uncertainty col:", self.uncertainty_col_edit)

        self.default_unc_spin = QDoubleSpinBox()
        self.default_unc_spin.setRange(0.1, 100.0)
        self.default_unc_spin.setValue(10.0)
        self.default_unc_spin.setSuffix(" m")
        fl.addRow("Default uncertainty:", self.default_unc_spin)

        root.addWidget(file_box)

        # ── Transect params ───────────────────────────────────────────────
        t_box = QGroupBox("Transect Parameters")
        tl = QFormLayout(t_box)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(10, 5000)
        self.spacing_spin.setValue(250)
        self.spacing_spin.setSuffix(" m")
        tl.addRow("Spacing:", self.spacing_spin)

        self.smoothing_spin = QSpinBox()
        self.smoothing_spin.setRange(100, 20000)
        self.smoothing_spin.setValue(4000)
        self.smoothing_spin.setSuffix(" m")
        tl.addRow("Smoothing:", self.smoothing_spin)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(500, 50000)
        self.length_spin.setValue(8000)
        self.length_spin.setSuffix(" m")
        tl.addRow("Transect length:", self.length_spin)

        root.addWidget(t_box)

        # ── Methods ───────────────────────────────────────────────────────
        m_box = QGroupBox("Methods")
        ml = QVBoxLayout(m_box)
        self.chk_rf       = QCheckBox("Random Forest benchmark")
        self.chk_rf.setChecked(True)
        self.chk_bayesian = QCheckBox("Bayesian changepoint (slow)")
        self.chk_bayesian.setChecked(False)
        ml.addWidget(self.chk_bayesian)
        self.chk_forecast = QCheckBox("Forecast")
        self.chk_forecast.setChecked(True)
        self.forecast_spin = QSpinBox()
        self.forecast_spin.setRange(1, 50)
        self.forecast_spin.setValue(10)
        self.forecast_spin.setSuffix(" yrs")
        frow = QHBoxLayout()
        frow.addWidget(self.chk_forecast)
        frow.addWidget(self.forecast_spin)
        ml.addWidget(self.chk_rf)
        ml.addLayout(frow)
        root.addWidget(m_box)

        # ── Run button ────────────────────────────────────────────────────
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.setFixedHeight(40)
        self.run_btn.setStyleSheet(
            "QPushButton { background:#2563eb; color:white; border-radius:6px; font-weight:bold; }"
            "QPushButton:hover { background:#1d4ed8; }"
            "QPushButton:disabled { background:#94a3b8; }"
        )
        self.run_btn.clicked.connect(self._emit_run)
        root.addWidget(self.run_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        root.addStretch()

    def _browse_shoreline(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Shoreline File", "",
            "Geo files (*.geojson *.shp *.gpkg);;All files (*)"
        )
        if path:
            self.shoreline_edit.setText(path)

    def _browse_baseline(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Baseline File", "",
            "Geo files (*.geojson *.shp *.gpkg);;All files (*)"
        )
        if path:
            self.baseline_edit.setText(path)

    def _emit_run(self):
        params = {
            "shoreline_path":      self.shoreline_edit.text(),
            "baseline_path":       self.baseline_edit.text(),
            "date_col":            self.date_col_edit.text(),
            "uncertainty_col":     self.uncertainty_col_edit.text(),
            "default_uncertainty": self.default_unc_spin.value(),
            "spacing":             self.spacing_spin.value(),
            "smoothing":           self.smoothing_spin.value(),
            "transect_length":     self.length_spin.value(),
            "run_rf":              self.chk_rf.isChecked(),
            "run_bayesian":        self.chk_bayesian.isChecked(),
            "run_forecast":        self.chk_forecast.isChecked(),
            "forecast_horizon":    self.forecast_spin.value(),
        }
        self.run_requested.emit(params)

    def set_status(self, msg: str):
        self.status_label.setText(msg)

    def set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.run_btn.setText("Running…" if running else "Run Analysis")
