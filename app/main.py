"""Entry point — launch SHIFT desktop app."""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
