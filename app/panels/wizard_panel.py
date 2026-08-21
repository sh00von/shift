"""
Step-by-step wizard panel.
Steps: 1-Import Shoreline → 2-Import Baseline → 3-Create Transects → 4-Run Analysis
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget, QFrame, QSizePolicy,
)


# ── Step indicator widget ──────────────────────────────────────────────────

class StepIndicator(QWidget):
    def __init__(self, steps: list[str], parent=None):
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        self._labels = []
        for i, name in enumerate(steps):
            row = QHBoxLayout()
            row.setSpacing(8)
            num = QLabel(str(i + 1))
            num.setFixedSize(26, 26)
            num.setAlignment(Qt.AlignCenter)
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#64748b;")
            row.addWidget(num)
            row.addWidget(lbl)
            row.addStretch()
            w = QWidget()
            w.setLayout(row)
            w.setFixedHeight(34)
            layout.addWidget(w)
            if i < len(steps) - 1:
                connector = QLabel("   │")
                connector.setStyleSheet("color:#cbd5e1; font-size:10px;")
                connector.setFixedHeight(12)
                layout.addWidget(connector)
            self._labels.append((num, lbl))
        layout.addStretch()
        self.refresh(0)

    def refresh(self, current: int):
        self._current = current
        for i, (num, lbl) in enumerate(self._labels):
            if i < current:
                num.setStyleSheet(
                    "QLabel{background:#22c55e;color:white;border-radius:13px;"
                    "font-weight:bold;font-size:12px;}")
                lbl.setStyleSheet("QLabel{color:#15803d;font-weight:bold;font-size:13px;}")
            elif i == current:
                num.setStyleSheet(
                    "QLabel{background:#2563eb;color:white;border-radius:13px;"
                    "font-weight:bold;font-size:12px;}")
                lbl.setStyleSheet("QLabel{color:#1d4ed8;font-weight:bold;font-size:13px;}")
            else:
                num.setStyleSheet(
                    "QLabel{background:#e2e8f0;color:#94a3b8;border-radius:13px;"
                    "font-size:12px;}")
                lbl.setStyleSheet("QLabel{color:#94a3b8;font-size:13px;}")


# ── Individual step pages ──────────────────────────────────────────────────

class Step1_Shoreline(QWidget):
    """Import shoreline file and select date / uncertainty columns."""
    file_loaded = Signal(str, list)   # path, column names

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = ""
        self.columns = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Step 1 — Import Shoreline File")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#1e3a5f;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            "Select a shoreline file (GeoJSON, Shapefile, or GeoPackage).\n"
            "Each feature must be a LineString representing a shoreline at one date."
        ))

        # File picker
        file_box = QGroupBox("Shoreline File")
        fl = QFormLayout(file_box)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("No file selected…")
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.setMinimumWidth(90)
        browse_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;border-radius:5px;"
            "padding:5px 12px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#1d4ed8;}"
        )
        browse_btn.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path_edit)
        row.addWidget(browse_btn)
        fl.addRow(row)
        layout.addWidget(file_box)

        # Column selectors (hidden until file loaded)
        self.col_box = QGroupBox("Column Mapping")
        cl = QFormLayout(self.col_box)
        self.date_combo = QComboBox()
        self.unc_combo  = QComboBox()
        self.unc_combo.addItem("(none — use default)")
        self.default_unc_spin = QDoubleSpinBox()
        self.default_unc_spin.setRange(0.1, 200.0)
        self.default_unc_spin.setValue(10.0)
        self.default_unc_spin.setSuffix(" m")
        cl.addRow("Date column:", self.date_combo)
        cl.addRow("Uncertainty column:", self.unc_combo)
        cl.addRow("Default uncertainty:", self.default_unc_spin)
        self.col_box.setVisible(False)
        layout.addWidget(self.col_box)

        # Preview info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "QLabel{background:#f0f9ff;border:1px solid #bae6fd;"
            "padding:8px;border-radius:4px;font-family:monospace;color:#0c4a6e;}"
        )
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)

        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Shoreline File", "",
            "Geo files (*.geojson *.shp *.gpkg);;All files (*)"
        )
        if not path:
            return
        try:
            gdf = gpd.read_file(path)
            cols = [c for c in gdf.columns if c != "geometry"]
            self.path = path
            self.columns = cols
            self.path_edit.setText(path)

            self.date_combo.clear()
            self.unc_combo.clear()
            self.unc_combo.addItem("(none — use default)")
            for c in cols:
                self.date_combo.addItem(c)
                self.unc_combo.addItem(c)

            # Auto-select likely columns
            for i, c in enumerate(cols):
                if "date" in c.lower():
                    self.date_combo.setCurrentIndex(i)
                if "uncertain" in c.lower():
                    self.unc_combo.setCurrentIndex(i + 1)

            n = len(gdf)
            crs = str(gdf.crs)
            geom_types = gdf.geometry.geom_type.unique().tolist()
            sample_dates = ""
            date_col = self.date_combo.currentText()
            if date_col in gdf.columns:
                sample_dates = "  |  Dates: " + ", ".join(str(v) for v in gdf[date_col].head(3))

            self.info_label.setText(
                f"File: {path.split('/')[-1].split(chr(92))[-1]}\n"
                f"Features: {n}  |  CRS: {crs}  |  Geometry: {geom_types}{sample_dates}"
            )
            self.col_box.setVisible(True)
            self.info_label.setVisible(True)
            self.file_loaded.emit(path, cols)
        except Exception as e:
            self.info_label.setText(f"Error loading file: {e}")
            self.info_label.setVisible(True)

    def get_params(self) -> dict:
        unc_col = self.unc_combo.currentText()
        if unc_col == "(none — use default)":
            unc_col = ""
        return {
            "shoreline_path":      self.path,
            "date_col":            self.date_combo.currentText(),
            "uncertainty_col":     unc_col,
            "default_uncertainty": self.default_unc_spin.value(),
        }


class Step2_Baseline(QWidget):
    """Import baseline file."""
    file_loaded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Step 2 — Import Baseline File")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#1e3a5f;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            "Select a baseline file — a line drawn roughly parallel to the coast.\n"
            "Transects will be cast perpendicular from this line."
        ))

        file_box = QGroupBox("Baseline File")
        fl = QFormLayout(file_box)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("No file selected…")
        self.path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.setMinimumWidth(90)
        browse_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;border-radius:5px;"
            "padding:5px 12px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#1d4ed8;}"
        )
        browse_btn.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path_edit)
        row.addWidget(browse_btn)
        fl.addRow(row)
        layout.addWidget(file_box)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "QLabel{background:#f0f9ff;border:1px solid #bae6fd;"
            "padding:8px;border-radius:4px;font-family:monospace;color:#0c4a6e;}"
        )
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)
        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Baseline File", "",
            "Geo files (*.geojson *.shp *.gpkg);;All files (*)"
        )
        if not path:
            return
        try:
            gdf = gpd.read_file(path)
            gdf = gdf.explode(index_parts=False)
            length = gdf.geometry.length.sum()
            self.path = path
            self.path_edit.setText(path)
            self.info_label.setText(
                f"File: {path.split('/')[-1].split(chr(92))[-1]}\n"
                f"CRS: {gdf.crs}  |  Length: {length/1000:.2f} km"
            )
            self.info_label.setVisible(True)
            self.file_loaded.emit(path)
        except Exception as e:
            self.info_label.setText(f"Error: {e}")
            self.info_label.setVisible(True)

    def get_params(self) -> dict:
        return {"baseline_path": self.path}


class Step3_Transects(QWidget):
    """Configure transect parameters."""
    preview_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Step 3 — Create Transects")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#1e3a5f;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            "Set transect parameters. Click 'Preview Transects' to see them on the map\n"
            "before running the full analysis."
        ))

        t_box = QGroupBox("Transect Parameters")
        tl = QFormLayout(t_box)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(10, 5000)
        self.spacing_spin.setValue(250)
        self.spacing_spin.setSuffix(" m")
        tl.addRow("Spacing (along-shore):", self.spacing_spin)

        self.smoothing_spin = QSpinBox()
        self.smoothing_spin.setRange(100, 20000)
        self.smoothing_spin.setValue(4000)
        self.smoothing_spin.setSuffix(" m")
        tl.addRow("Smoothing distance:", self.smoothing_spin)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(500, 50000)
        self.length_spin.setValue(8000)
        self.length_spin.setSuffix(" m")
        tl.addRow("Transect length:", self.length_spin)

        layout.addWidget(t_box)

        preview_btn = QPushButton("Preview Transects on Map")
        preview_btn.setStyleSheet(
            "QPushButton{background:#0ea5e9;color:white;border-radius:6px;"
            "padding:8px;font-weight:bold;}"
            "QPushButton:hover{background:#0284c7;}"
        )
        preview_btn.clicked.connect(
            lambda: self.preview_requested.emit(self.get_params())
        )
        layout.addWidget(preview_btn)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "background:#f0fdf4;border:1px solid #bbf7d0;"
            "padding:8px;border-radius:4px;font-family:monospace;"
        )
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)
        layout.addStretch()

    def set_preview_result(self, n_transects: int):
        self.info_label.setText(
            f"Transects created: {n_transects}  "
            f"(spacing {self.spacing_spin.value()} m, "
            f"smoothing {self.smoothing_spin.value()} m, "
            f"length {self.length_spin.value()} m)\n"
            f"Transects are shown on the map. Click Next to run analysis."
        )
        self.info_label.setVisible(True)

    def get_params(self) -> dict:
        return {
            "spacing":         self.spacing_spin.value(),
            "smoothing":       self.smoothing_spin.value(),
            "transect_length": self.length_spin.value(),
        }


class Step4_Analysis(QWidget):
    """Choose methods and run."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Step 4 — Run Analysis")
        title.setStyleSheet("font-size:15px;font-weight:bold;color:#1e3a5f;")
        layout.addWidget(title)

        layout.addWidget(QLabel(
            "Select which statistical methods to run.\n"
            "Classic metrics (EPR/LRR/WLR) and Breakpoint are always included."
        ))

        m_box = QGroupBox("Methods")
        ml = QVBoxLayout(m_box)

        always = QLabel("✔  Classic metrics (EPR / LRR / WLR / NSM / SCE)")
        always.setStyleSheet("color:#15803d;font-weight:bold;")
        ml.addWidget(always)

        always2 = QLabel("✔  Breakpoint regression (primary contribution)")
        always2.setStyleSheet("color:#15803d;font-weight:bold;")
        ml.addWidget(always2)

        self.chk_bayesian = QCheckBox(
            "Bayesian changepoint  (PyMC — slow, ~2 min for 383 transects)"
        )
        self.chk_bayesian.setChecked(False)
        ml.addWidget(self.chk_bayesian)

        self.chk_rf = QCheckBox("Random Forest benchmark")
        self.chk_rf.setChecked(True)
        ml.addWidget(self.chk_rf)

        layout.addWidget(m_box)

        f_box = QGroupBox("Forecast")
        fl = QFormLayout(f_box)
        self.chk_forecast = QCheckBox("Generate forecast")
        self.chk_forecast.setChecked(True)
        self.horizon_spin = QSpinBox()
        self.horizon_spin.setRange(1, 50)
        self.horizon_spin.setValue(10)
        self.horizon_spin.setSuffix(" years")
        fl.addRow(self.chk_forecast)
        fl.addRow("Horizon:", self.horizon_spin)
        layout.addWidget(f_box)
        layout.addStretch()

    def get_params(self) -> dict:
        return {
            "run_bayesian":     self.chk_bayesian.isChecked(),
            "run_rf":           self.chk_rf.isChecked(),
            "run_forecast":     self.chk_forecast.isChecked(),
            "forecast_horizon": self.horizon_spin.value(),
        }


# ── Main wizard widget ─────────────────────────────────────────────────────

class WizardPanel(QWidget):
    """
    Hosts step indicator + stacked pages + Next/Back navigation.
    Emits signals consumed by MainWindow.
    """
    preview_transects_requested = Signal(dict)   # all params so far
    run_requested               = Signal(dict)   # all params combined
    status_message              = Signal(str)

    STEP_NAMES = [
        "Import Shoreline",
        "Import Baseline",
        "Create Transects",
        "Run Analysis",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Step indicator
        self.indicator = StepIndicator(self.STEP_NAMES)
        self.indicator.setContentsMargins(12, 12, 12, 4)
        root.addWidget(self.indicator)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color:#e2e8f0;")
        root.addWidget(div)

        # Step pages
        self.stack = QStackedWidget()
        self.step1 = Step1_Shoreline()
        self.step2 = Step2_Baseline()
        self.step3 = Step3_Transects()
        self.step4 = Step4_Analysis()
        for s in [self.step1, self.step2, self.step3, self.step4]:
            self.stack.addWidget(s)
        root.addWidget(self.stack, 1)

        # Connect step3 preview
        self.step3.preview_requested.connect(self._on_preview)

        # Nav buttons
        nav = QHBoxLayout()
        nav.setContentsMargins(12, 8, 12, 12)
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedHeight(36)
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setEnabled(False)
        self.next_btn = QPushButton("Next →")
        self.next_btn.setFixedHeight(36)
        self.next_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;border-radius:6px;font-weight:bold;}"
            "QPushButton:hover{background:#1d4ed8;}"
            "QPushButton:disabled{background:#94a3b8;}"
        )
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        # Status
        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setContentsMargins(12, 0, 12, 8)
        self.status_lbl.setStyleSheet("color:#64748b;font-size:11px;")
        root.addWidget(self.status_lbl)

    def _go_next(self):
        if self._current == 3:
            self._emit_run()
            return
        # Validate current step
        if self._current == 0 and not self.step1.path:
            self.status_lbl.setText("Please select a shoreline file first.")
            return
        if self._current == 1 and not self.step2.path:
            self.status_lbl.setText("Please select a baseline file first.")
            return
        self.status_lbl.setText("")
        self._current += 1
        self.stack.setCurrentIndex(self._current)
        self.indicator.refresh(self._current)
        self.back_btn.setEnabled(True)
        if self._current == 3:
            self.next_btn.setText("Run Analysis ▶")
            self.next_btn.setStyleSheet(
                "QPushButton{background:#16a34a;color:white;border-radius:6px;font-weight:bold;}"
                "QPushButton:hover{background:#15803d;}"
                "QPushButton:disabled{background:#94a3b8;}"
            )

    def _go_back(self):
        if self._current == 0:
            return
        self._current -= 1
        self.stack.setCurrentIndex(self._current)
        self.indicator.refresh(self._current)
        self.back_btn.setEnabled(self._current > 0)
        self.next_btn.setText("Next →")
        self.next_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:white;border-radius:6px;font-weight:bold;}"
            "QPushButton:hover{background:#1d4ed8;}"
            "QPushButton:disabled{background:#94a3b8;}"
        )

    def _on_preview(self, t_params: dict):
        params = {**self.step1.get_params(), **self.step2.get_params(), **t_params}
        self.preview_transects_requested.emit(params)

    def _emit_run(self):
        params = {
            **self.step1.get_params(),
            **self.step2.get_params(),
            **self.step3.get_params(),
            **self.step4.get_params(),
        }
        self.run_requested.emit(params)

    def set_status(self, msg: str):
        self.status_lbl.setText(msg)

    def set_running(self, running: bool):
        self.next_btn.setEnabled(not running)
        self.back_btn.setEnabled(not running)
        if running:
            self.next_btn.setText("Running…")

    def set_preview_done(self, n_transects: int):
        self.step3.set_preview_result(n_transects)
