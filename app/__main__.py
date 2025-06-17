#!/usr/bin/env python3
"""Application entry point for SheetPilot."""

import sys
from PyQt5.QtWidgets import QApplication
from app.gui.main_window import MainWindow


def main():
    """Launch the SheetPilot GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("SheetPilot")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
