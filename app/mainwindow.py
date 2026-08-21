"""Main application window — wizard-driven step-by-step workflow."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget, QMainWindow, QMessageBox,
    QStatusBar, QTabWidget,
)

from app.panels.wizard_panel     import WizardPanel
from app.panels.map_panel        import MapPanel
from app.panels.results_panel    import ResultsPanel
from app.panels.comparison_panel import ComparisonPanel
from app.worker                  import AnalysisWorker, PreviewWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "SHIFT — Statistical Changepoint Framework for Shoreline Analysis"
        )
        self.resize(1400, 860)
        self._analysis_worker = None
        self._preview_worker  = None
        self._build_ui()

    def _build_ui(self):
        # ── Wizard dock (left) ────────────────────────────────────────────
        self.wizard = WizardPanel()
        self.wizard.preview_transects_requested.connect(self._on_preview)
        self.wizard.run_requested.connect(self._on_run)

        dock = QDockWidget("Workflow", self)
        dock.setWidget(self.wizard)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        )
        dock.setMinimumWidth(340)
        dock.setMaximumWidth(420)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

        # ── Central tabs ──────────────────────────────────────────────────
        self.map_panel        = MapPanel()
        self.results_panel    = ResultsPanel()
        self.comparison_panel = ComparisonPanel()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.map_panel,        "Map")
        self.tabs.addTab(self.results_panel,    "Transect Results")
        self.tabs.addTab(self.comparison_panel, "Method Comparison")
        self.setCentralWidget(self.tabs)

        # ── Status bar ────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            "Step 1 — Import your shoreline file to begin."
        )

        # ── Stylesheet ────────────────────────────────────────────────────
        self.setStyleSheet("""
            QMainWindow, QWidget   { background:#f8fafc; }
            QDockWidget::title     {
                background:#1e3a5f; color:white;
                padding:8px; font-weight:bold; font-size:13px;
            }
            QGroupBox {
                border:1px solid #cbd5e1; border-radius:6px;
                margin-top:10px; padding:10px;
                font-weight:bold; color:#334155;
            }
            QGroupBox::title { subcontrol-origin:margin; left:10px; }
            QTabWidget::pane { border:1px solid #cbd5e1; border-radius:4px; }
            QTabBar::tab {
                background:#e2e8f0; padding:7px 18px;
                border-top-left-radius:4px; border-top-right-radius:4px;
                font-weight:bold; color:#475569;
            }
            QTabBar::tab:selected  { background:#1e3a5f; color:white; }
            QTabBar::tab:hover     { background:#94a3b8; color:white; }
            QStatusBar             { background:#1e3a5f; color:white; padding:4px; }
            QPushButton            {
                border:1px solid #cbd5e1; border-radius:5px;
                padding:5px 12px; background:#f1f5f9; color:#1e293b;
            }
            QPushButton:hover      { background:#e2e8f0; color:#1e293b; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border:1px solid #cbd5e1; border-radius:4px;
                padding:4px 6px; background:white;
            }
            QComboBox::drop-down   { border:none; }
        """)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_preview(self, params: dict):
        self.wizard.set_status("Generating transect preview…")
        self.status.showMessage("Casting transects…")
        self._preview_worker = PreviewWorker(params)
        self._preview_worker.finished.connect(self._on_preview_done)
        self._preview_worker.error.connect(self._on_error)
        self._preview_worker.start()

    def _on_preview_done(self, transects):
        n = len(transects)
        self.wizard.set_preview_done(n)
        self.status.showMessage(f"{n} transects created — shown on map.")
        # Show transects on map (no results yet)
        self.map_panel.show_transects_only(transects)
        self.tabs.setCurrentIndex(0)   # switch to Map tab

    def _on_run(self, params: dict):
        self.wizard.set_running(True)
        self.status.showMessage("Running analysis…")
        self._analysis_worker = AnalysisWorker(params)
        self._analysis_worker.progress.connect(self._on_progress)
        self._analysis_worker.finished.connect(self._on_finished)
        self._analysis_worker.error.connect(self._on_error)
        self._analysis_worker.start()

    def _on_progress(self, msg: str):
        self.wizard.set_status(msg)
        self.status.showMessage(msg)

    def _on_finished(self, series_list, results, transects):
        self.wizard.set_running(False)
        n = len(series_list)
        self.wizard.set_status(f"Done — {n} transects analysed.")
        self.status.showMessage(f"Analysis complete — {n} transects.")
        self.map_panel.load_results(series_list, results, transects)
        self.results_panel.load_results(series_list, results)
        self.comparison_panel.load_results(series_list, results)
        self.tabs.setCurrentIndex(0)

    def _on_error(self, tb: str):
        self.wizard.set_running(False)
        self.wizard.set_status("Error — see details.")
        self.status.showMessage("Error during analysis.")
        QMessageBox.critical(self, "Error", tb)
