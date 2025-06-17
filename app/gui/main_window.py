"""Main application window."""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QMenuBar, QMenu, QAction, QStatusBar
)
from PyQt5.QtCore import Qt
import pandas as pd

from .import_window import ImportWindow
from .config_window import ConfigWindow
from .report_window import ReportWindow


class MainWindow(QMainWindow):
    """Main application window with navigation."""
    
    def __init__(self):
        super().__init__()
        self.df = None
        self.cleaned_df = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("SheetPilot")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create windows
        self.import_window = ImportWindow()
        self.config_window = ConfigWindow()
        self.report_window = ReportWindow()
        
        # Add windows to stack
        self.stacked_widget.addWidget(self.import_window)
        self.stacked_widget.addWidget(self.config_window)
        self.stacked_widget.addWidget(self.report_window)
        
        # Connect signals
        self.import_window.data_imported.connect(self.on_data_imported)
        self.config_window.cleaning_completed.connect(self.on_cleaning_completed)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        import_action = QAction("Import Data", self)
        import_action.triggered.connect(self.show_import_window)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        import_view = QAction("Data Import", self)
        import_view.triggered.connect(self.show_import_window)
        view_menu.addAction(import_view)
        
        config_view = QAction("Cleaning Config", self)
        config_view.triggered.connect(self.show_config_window)
        view_menu.addAction(config_view)
        
        report_view = QAction("Report", self)
        report_view.triggered.connect(self.show_report_window)
        view_menu.addAction(report_view)
        
    def show_import_window(self):
        """Switch to import window."""
        self.stacked_widget.setCurrentWidget(self.import_window)
        
    def show_config_window(self):
        """Switch to config window."""
        if self.df is not None:
            self.stacked_widget.setCurrentWidget(self.config_window)
        else:
            self.status_bar.showMessage("Please import data first")
            
    def show_report_window(self):
        """Switch to report window."""
        if self.cleaned_df is not None:
            self.stacked_widget.setCurrentWidget(self.report_window)
        else:
            self.status_bar.showMessage("No cleaning results available")
            
    def on_data_imported(self, df: pd.DataFrame):
        """Handle data import completion."""
        self.df = df
        self.config_window.set_dataframe(df)
        self.show_config_window()
        self.status_bar.showMessage(
            f"Data imported: {len(df)} rows, {len(df.columns)} columns"
        )
        
    def on_cleaning_completed(self, df: pd.DataFrame, report):
        """Handle cleaning completion."""
        self.cleaned_df = df
        self.report_window.set_results(df, report)
        self.show_report_window()
        self.status_bar.showMessage("Cleaning completed")
