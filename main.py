#!/usr/bin/env python3
"""TARDIS - Transient Absorption Rapid Data Integration System.

Entry point for the transient absorption spectroscopy GUI application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from tardis.gui import MainWindow


def main():
    """Run the TARDIS application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("TARDIS")
    app.setApplicationVersion("0.1.0")

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
