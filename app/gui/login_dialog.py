from PyQt5 import QtWidgets, QtCore

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("SheetPilot - Login")
        self.setModal(True) # Block other windows until login is done

        layout = QtWidgets.QVBoxLayout(self)

        # Form layout for username and password
        form_layout = QtWidgets.QFormLayout()

        self.username_label = QtWidgets.QLabel("Username:")
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        form_layout.addRow(self.username_label, self.username_input)

        self.password_label = QtWidgets.QLabel("Password:")
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addRow(self.password_label, self.password_input)

        layout.addLayout(form_layout)

        # Status label for errors
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.login_button = QtWidgets.QPushButton("Login")
        self.login_button.setDefault(True) # Default button on Enter press

        self.cancel_button = QtWidgets.QPushButton("Cancel")

        button_layout.addStretch()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Connect signals
        self.login_button.clicked.connect(self.on_login_attempt)
        self.cancel_button.clicked.connect(self.reject) # Built-in reject slot closes dialog

        # Allow Enter key on password field to trigger login
        self.password_input.returnPressed.connect(self.on_login_attempt)

        self.setMinimumWidth(300)

    def on_login_attempt(self):
        """
        Called when the login button is clicked or Enter is pressed.
        It validates inputs and then accepts the dialog.
        The actual authentication logic will be handled by the caller based on dialog.accept().
        """
        username = self.get_username()
        password = self.get_password()

        if not username or not password:
            self.set_status_message("Username and password cannot be empty.")
            return

        # If inputs are present, accept the dialog.
        # The main app will then get credentials and call login_user.
        self.accept()

    def get_username(self) -> str:
        return self.username_input.text().strip()

    def get_password(self) -> str:
        return self.password_input.text() # No strip, as passwords can have spaces

    def set_status_message(self, message: str):
        self.status_label.setText(message)
        if message: # Make sure status label is visible if there's a message
            self.status_label.show()
        else:
            self.status_label.hide() # Hide if no message to save space

if __name__ == '__main__':
    # Example usage:
    import sys
    app = QtWidgets.QApplication(sys.argv)

    dialog = LoginDialog()

    # This is how the main application would use it:
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        print("Login attempt with:")
        print(f"Username: {dialog.get_username()}")
        print(f"Password: {dialog.get_password()}")
        # Here, the main app would call `login_user(username, password)`
        # and if it fails, it might re-show the dialog or update its status.
        # For this example, we just print.
        if dialog.get_username() == "test" and dialog.get_password() == "pass":
            print("Simulated successful login.")
        else:
            print("Simulated failed login. Main app would show error on dialog here.")
            # dialog.set_status_message("Login failed! (Example)")
            # dialog.show() # Or re-open if necessary.
            # A better pattern is to keep the dialog open and update status from the main app loop.
    else:
        print("Login dialog cancelled.")

    # sys.exit(app.exec_()) # Not needed for this example print
