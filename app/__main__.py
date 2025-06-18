#!/usr/bin/env python3
"""Application entry point for SheetPilot."""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox

from app.gui.main_window import MainWindow
from app.gui.login_dialog import LoginDialog
from app.core.user_management import login_user, init_db as init_user_db

# Ensure user database is initialized on startup
# init_user_db() is also called when user_management is imported,
# but calling it here explicitly ensures it's done before any GUI.
try:
    init_user_db()
except Exception as e:
    # If DB init fails catastrophically, show error and exit.
    # This requires QApplication to be created first for QMessageBox.
    # A more robust solution might involve a pre-QApplication check or logging to a file.
    temp_app_for_error = QApplication.instance() # Check if an instance already exists
    if temp_app_for_error is None:
        temp_app_for_error = QApplication(sys.argv)

    QMessageBox.critical(
        None,
        "Database Error",
        f"Could not initialize the user database: {e}\n"
        "Please check permissions and disk space in ~/.sheetpilot/",
        QMessageBox.Ok
    )
    sys.exit(1)


def main():
    """Launch the SheetPilot GUI application with login."""
    app = QApplication(sys.argv)
    app.setApplicationName("SheetPilot")

    current_user = None
    login_dialog = LoginDialog()

    while True: # Loop to allow login retries
        if login_dialog.exec_() == QtWidgets.QDialog.Accepted:
            username = login_dialog.get_username()
            password = login_dialog.get_password()

            user_data = login_user(username, password)

            if user_data:
                current_user = user_data
                login_dialog.set_status_message("") # Clear any previous error
                login_dialog.accept() # Close the dialog formally
                break # Exit loop on successful login
            else:
                login_dialog.set_status_message("Login failed. Invalid username or password.")
                # Dialog remains open for another attempt due to the loop
        else:
            # Login dialog was cancelled or closed
            sys.exit(0) # Exit application gracefully

    if current_user:
        main_window = MainWindow(current_user=current_user) # Pass user to main window
        main_window.show()
        sys.exit(app.exec_())
    else:
        # Should not be reached if loop logic is correct, but as a fallback:
        QMessageBox.critical(None, "Login Error", "Login failed. Application will exit.", QMessageBox.Ok)
        sys.exit(1)


if __name__ == "__main__":
    main()
