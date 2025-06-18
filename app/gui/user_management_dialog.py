from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox

from app.core.user_management import (
    list_users,
    add_user,
    update_user_role,
    delete_user,
    update_user_password, # For potential future "Reset Password"
    ROLES_PERMISSIONS # To get available roles for dropdowns
)
# Audit logging imports
from app.core.audit_logger import (
    log_audit_event,
    ACTION_ADMIN_INITIATED_USER_ADDITION,
    ACTION_ADMIN_INITIATED_ROLE_UPDATE,
    ACTION_ADMIN_INITIATED_USER_DELETION
)

class UserManagementDialog(QtWidgets.QDialog):
    def __init__(self, current_admin_user: dict, parent=None): # Changed to current_admin_user (dict)
        super().__init__(parent)
        self.current_admin_user = current_admin_user # Store the full admin user object
        self.current_admin_username = current_admin_user.get('username') if current_admin_user else "UnknownAdmin"


        self.setWindowTitle("User Management")
        self.setMinimumSize(600, 400)

        self.init_ui()
        self.populate_user_list()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # User Table
        self.user_table = QtWidgets.QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["Username", "Role", "Created At"])
        self.user_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.user_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.user_table.verticalHeader().setVisible(False)
        layout.addWidget(self.user_table)

        # Action Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.add_user_button = QtWidgets.QPushButton("Add User")
        self.edit_role_button = QtWidgets.QPushButton("Edit Role")
        self.delete_user_button = QtWidgets.QPushButton("Delete User")
        self.reset_password_button = QtWidgets.QPushButton("Reset Password") # Optional for now
        self.refresh_button = QtWidgets.QPushButton("Refresh List")

        button_layout.addWidget(self.add_user_button)
        button_layout.addWidget(self.edit_role_button)
        button_layout.addWidget(self.delete_user_button)
        # button_layout.addWidget(self.reset_password_button) # Add when implemented
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        self.close_button = QtWidgets.QPushButton("Close")
        layout.addWidget(self.close_button, alignment=QtCore.Qt.AlignRight)

        # Connect signals
        self.add_user_button.clicked.connect(self.handle_add_user)
        self.edit_role_button.clicked.connect(self.handle_edit_role)
        self.delete_user_button.clicked.connect(self.handle_delete_user)
        self.refresh_button.clicked.connect(self.populate_user_list)
        self.close_button.clicked.connect(self.accept)
        # self.reset_password_button.clicked.connect(self.handle_reset_password)

        # Enable/disable buttons based on selection
        self.user_table.itemSelectionChanged.connect(self.update_button_states)
        self.update_button_states() # Initial state

    def update_button_states(self):
        selected_items = self.user_table.selectedItems()
        is_user_selected = bool(selected_items)

        self.edit_role_button.setEnabled(is_user_selected)
        self.delete_user_button.setEnabled(is_user_selected)
        # self.reset_password_button.setEnabled(is_user_selected)

    def populate_user_list(self):
        self.user_table.setRowCount(0) # Clear existing rows
        try:
            users = list_users()
            for row_num, user_data in enumerate(users):
                self.user_table.insertRow(row_num)
                self.user_table.setItem(row_num, 0, QtWidgets.QTableWidgetItem(user_data.get("username", "")))
                self.user_table.setItem(row_num, 1, QtWidgets.QTableWidgetItem(user_data.get("role", "")))
                self.user_table.setItem(row_num, 2, QtWidgets.QTableWidgetItem(str(user_data.get("created_at", ""))))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load users: {e}")

    def get_selected_username(self):
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            return None
        return self.user_table.item(selected_items[0].row(), 0).text() # Username is in column 0

    def handle_add_user(self):
        dialog = AddUserSubDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_username, password, role = dialog.get_details()
            if not new_username or not password:
                QMessageBox.warning(self, "Input Error", "Username and password cannot be empty.")
                return

            # Log admin's attempt to add user
            log_audit_event(
                action_type=ACTION_ADMIN_INITIATED_USER_ADDITION, outcome='ATTEMPT',
                user_id=self.current_admin_user.get('id'),
                username=self.current_admin_user.get('username'),
                details={'target_username': new_username, 'role': role}
            )

            if add_user(new_username, password, role): # add_user itself logs USER_CREATED outcome
                QMessageBox.information(self, "Success", f"User '{new_username}' added successfully.")
                self.populate_user_list()
            else:
                # add_user logs specific errors (e.g. duplicate username) and ACTION_USER_CREATE_FAILED
                QMessageBox.critical(self, "Error", f"Failed to add user '{new_username}'. See application logs for details.")

    def handle_edit_role(self):
        target_username = self.get_selected_username()
        if not target_username:
            QMessageBox.warning(self, "Selection Error", "Please select a user to edit.")
            return

        current_user_data = next((user for user in list_users() if user['username'] == target_username), None)
        if not current_user_data:
             QMessageBox.critical(self, "Error", f"Could not retrieve data for user {target_username}.")
             return
        current_role = current_user_data.get('role')

        dialog = EditRoleSubDialog(target_username, current_role, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_role = dialog.get_new_role()

            # Log admin's attempt to update role
            log_audit_event(
                action_type=ACTION_ADMIN_INITIATED_ROLE_UPDATE, outcome='ATTEMPT',
                user_id=self.current_admin_user.get('id'),
                username=self.current_admin_user.get('username'),
                details={'target_username': target_username, 'old_role': current_role, 'new_role': new_role}
            )

            if update_user_role(target_username, new_role): # update_user_role logs USER_ROLE_UPDATED outcome
                QMessageBox.information(self, "Success", f"Role for '{target_username}' updated to '{new_role}'.")
                self.populate_user_list()
            else:
                # update_user_role logs ACTION_USER_ROLE_UPDATE_FAILED
                QMessageBox.critical(self, "Error", f"Failed to update role for '{target_username}'.")

    def handle_delete_user(self):
        target_username = self.get_selected_username()
        if not target_username:
            QMessageBox.warning(self, "Selection Error", "Please select a user to delete.")
            return

        if target_username == self.current_admin_username: # Check against the stored username
            QMessageBox.critical(self, "Action Denied", "You cannot delete your own currently logged-in admin account.")
            return

        reply = QMessageBox.confirm(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete user '{target_username}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Log admin's attempt to delete user
            log_audit_event(
                action_type=ACTION_ADMIN_INITIATED_USER_DELETION, outcome='ATTEMPT',
                user_id=self.current_admin_user.get('id'),
                username=self.current_admin_user.get('username'),
                details={'target_username': target_username}
            )

            if delete_user(target_username): # delete_user logs USER_DELETED outcome
                QMessageBox.information(self, "Success", f"User '{target_username}' deleted successfully.")
                self.populate_user_list()
            else:
                # delete_user logs ACTION_USER_DELETE_FAILED
                QMessageBox.critical(self, "Error", f"Failed to delete user '{target_username}'.")

    # Placeholder for Reset Password
    # def handle_reset_password(self):
    #     username = self.get_selected_username()
    #     if not username:
    #         QMessageBox.warning(self, "Selection Error", "Please select a user.")
    #         return
    #     # Similar dialog flow as add/edit for getting new password
    #     QMessageBox.information(self, "Not Implemented", "Reset password functionality is not yet implemented.")


# --- Sub-Dialog for Add User ---
class AddUserSubDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New User")
        layout = QtWidgets.QFormLayout(self)

        self.username_input = QtWidgets.QLineEdit()
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.role_combo = QtWidgets.QComboBox()
        self.role_combo.addItems(sorted(ROLES_PERMISSIONS.keys())) # Populate from defined roles

        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        layout.addRow("Role:", self.role_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_details(self):
        return self.username_input.text().strip(), self.password_input.text(), self.role_combo.currentText()

# --- Sub-Dialog for Edit Role ---
class EditRoleSubDialog(QtWidgets.QDialog):
    def __init__(self, username, current_role, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Role for {username}")
        layout = QtWidgets.QFormLayout(self)

        self.username_label = QtWidgets.QLabel(username)
        self.role_combo = QtWidgets.QComboBox()
        self.role_combo.addItems(sorted(ROLES_PERMISSIONS.keys()))
        if current_role in ROLES_PERMISSIONS:
            self.role_combo.setCurrentText(current_role)

        layout.addRow("Username:", self.username_label)
        layout.addRow("New Role:", self.role_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_new_role(self):
        return self.role_combo.currentText()


if __name__ == '__main__':
    import sys
    # This import is for the example, ensure user_management.py is in PYTHONPATH
    # For real execution, the app structure handles this.
    from app.core.user_management import init_db

    # Ensure DB is initialized and a dummy admin exists for testing the dialog
    # In a real app, this is handled by main.py and login.
    app_for_example = QtWidgets.QApplication.instance()
    if not app_for_example:
        app_for_example = QtWidgets.QApplication(sys.argv)

    # IMPORTANT: This example requires a running DB setup.
    # The UserManagementDialog expects the DB to be initialized.
    # For this __main__ block to work standalone, you might need to ensure
    # that app.core.user_management.init_db() has been called successfully.
    # And a user (e.g. the 'admin' running this) exists.

    # Simplified init_db for example, real one is in user_management
    # if not (Path.home() / ".sheetpilot" / "user_data.db").exists():
    #     print("Initializing database for example...")
    #     init_db() # From user_management
    #     add_user("example_admin", "adminpass", "admin") # Add a test admin
    #     add_user("example_user", "userpass", "user")

    # dialog = UserManagementDialog(current_admin_username="example_admin") # Pass a dummy admin name
    # dialog.exec_()

    # The above direct execution is complex due to DB state.
    # It's better to test this dialog by running the main application
    # and logging in as an admin.

    info_label = QtWidgets.QLabel("This dialog is best tested by running the main application and logging in as an admin.")
    info_label.setWordWrap(True)
    info_label.show()
    sys.exit(app_for_example.exec_())
