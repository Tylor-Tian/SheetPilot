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
from .user_management_dialog import UserManagementDialog # Import the new dialog

# RBAC import
from app.core.user_management import has_permission
# Audit logging import
from app.core.audit_logger import log_audit_event, ACTION_ADMIN_ACCESS_USER_MANAGEMENT


class MainWindow(QMainWindow):
    """Main application window with navigation."""
    
    def __init__(self, current_user: dict = None): # Add current_user parameter
        super().__init__()
        self.current_user = current_user
        self.df = None
        self.cleaned_df = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        base_title = "SheetPilot"
        if self.current_user:
            user_info = f"{self.current_user.get('username', 'Unknown')} ({self.current_user.get('role', 'user')})"
            self.setWindowTitle(f"{base_title} - Logged in as: {user_info}")
        else:
            self.setWindowTitle(base_title) # Fallback if no user info

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
        # Pass current_user to ConfigWindow constructor
        self.config_window = ConfigWindow(current_user=self.current_user)
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
        
        # File menu -> User Management Action (placeholder)
        self.user_management_action = QAction("User Management", self)
        self.user_management_action.triggered.connect(self.open_user_management_dialog)
        file_menu.addAction(self.user_management_action)

        # Set initial enabled state based on permissions
        if self.current_user and \
           has_permission(self.current_user.get('role'), 'manage_users'):
            self.user_management_action.setEnabled(True)
        else:
            self.user_management_action.setEnabled(False)
            self.user_management_action.setToolTip("Requires admin privileges")


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

    def open_user_management_dialog(self):
        """Opens the User Management dialog if the current user has permission."""
        if self.current_user and has_permission(self.current_user.get('role'), 'manage_users'):
            log_audit_event(
                action_type=ACTION_ADMIN_ACCESS_USER_MANAGEMENT,
                outcome='SUCCESS',
                user_id=self.current_user.get('id'),
                username=self.current_user.get('username'),
                details={'message': 'Admin accessed User Management Dialog.'}
            )
            # Pass the full current_user object to the dialog
            dialog = UserManagementDialog(current_admin_user=self.current_user, parent=self)
            dialog.exec_() # Show the dialog modally
        else:
            # This check is technically redundant if the action is disabled,
            # but serves as a safeguard or if called from elsewhere.
            QtWidgets.QMessageBox.warning(
                self,
                "Permission Denied",
                "You do not have sufficient permissions to manage users."
            )
            self.status_bar.showMessage("User Management: Permission Denied.")
