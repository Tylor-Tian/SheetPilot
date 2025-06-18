import sqlite3
from pathlib import Path
import logging
import datetime # Will be used for created_at if we make it Python-driven
import bcrypt
from .audit_logger import (
    log_audit_event,
    ACTION_USER_LOGIN_SUCCESS, ACTION_USER_LOGIN_FAILURE,
    ACTION_USER_CREATED, ACTION_USER_CREATE_FAILED,
    ACTION_USER_ROLE_UPDATED, ACTION_USER_ROLE_UPDATE_FAILED,
    ACTION_USER_PASSWORD_UPDATED, ACTION_USER_PASSWORD_UPDATE_FAILED,
    ACTION_USER_DELETED, ACTION_USER_DELETE_FAILED
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
DATABASE_DIR = Path.home() / ".sheetpilot"
DATABASE_PATH = DATABASE_DIR / "user_data.db"

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
    conn = None
    try:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensuring database directory exists at: {DATABASE_DIR}")

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        logger.info(f"Database initialized and 'users' table ensured at: {DATABASE_PATH}")

    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

# --- Secure Password Hashing ---
def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password_from_db: str) -> bool:
    """Verifies a plain password against a stored hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_from_db.encode('utf-8'))
    except ValueError: # Handles cases where hashed_password_from_db is not a valid hash
        logger.warning("Encountered ValueError during password verification, possibly due to invalid hash format.")
        return False


# --- CRUD Operations ---

def _get_db_connection():
    """Helper function to get a database connection."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row # To access columns by name
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise

def add_user(username: str, plain_password: str, role: str = 'user') -> bool:
    """Adds a new user to the database with a securely hashed password."""
    hashed_pwd = hash_password(plain_password) # Uses new bcrypt hashing
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
            (username, hashed_pwd, role)
        )
        conn.commit()
        logger.info(f"User '{username}' added successfully with role '{role}'.")
        log_audit_event(
            action_type=ACTION_USER_CREATED, outcome='SUCCESS',
            username=username,
            details={'role': role, 'message': 'User account created.'}
        )
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"Failed to add user '{username}': Username already exists.")
        log_audit_event(
            action_type=ACTION_USER_CREATE_FAILED, outcome='FAILURE',
            username=username,
            details={'role': role, 'reason': 'Username already exists.'}
        )
        return False
    except sqlite3.Error as e:
        logger.error(f"Error adding user '{username}': {e}", exc_info=True)
        log_audit_event(
            action_type=ACTION_USER_CREATE_FAILED, outcome='FAILURE',
            username=username,
            details={'role': role, 'reason': f'Database error: {e}'}
        )
        return False
    finally:
        if conn:
            conn.close()

def get_user_by_username(username: str) -> dict or None:
    """Fetches a user by username, including all details."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password, role, created_at FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if user_row:
            return dict(user_row)
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user '{username}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id: int) -> dict or None:
    """Fetches a user by ID, including all details."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, hashed_password, role, created_at FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if user_row:
            return dict(user_row)
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user ID '{user_id}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def update_user_role(username: str, new_role: str) -> bool:
    """Updates the role for a given username."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Role for user '{username}' updated to '{new_role}'.")
            log_audit_event(
                action_type=ACTION_USER_ROLE_UPDATED, outcome='SUCCESS',
                username=username,
                details={'new_role': new_role, 'message': f'User role updated to {new_role}.'}
            )
            return True
        else:
            logger.warning(f"Failed to update role for '{username}': User not found or role unchanged.")
            log_audit_event(
                action_type=ACTION_USER_ROLE_UPDATE_FAILED, outcome='FAILURE',
                username=username,
                details={'new_role': new_role, 'reason': 'User not found or role unchanged.'}
            )
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating role for user '{username}': {e}", exc_info=True)
        log_audit_event(
            action_type=ACTION_USER_ROLE_UPDATE_FAILED, outcome='FAILURE',
            username=username,
            details={'new_role': new_role, 'reason': f'Database error: {e}'}
        )
        return False
    finally:
        if conn:
            conn.close()

def update_user_password(username: str, new_plain_password: str) -> bool:
    """Updates the password for a given username with a securely hashed new password."""
    new_hashed_password = hash_password(new_plain_password) # Uses new bcrypt hashing
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hashed_password = ? WHERE username = ?", (new_hashed_password, username))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Password for user '{username}' updated successfully.")
            log_audit_event(
                action_type=ACTION_USER_PASSWORD_UPDATED, outcome='SUCCESS',
                username=username,
                details={'message': 'User password changed successfully.'}
            )
            return True
        else:
            logger.warning(f"Failed to update password for '{username}': User not found.")
            log_audit_event(
                action_type=ACTION_USER_PASSWORD_UPDATE_FAILED, outcome='FAILURE',
                username=username,
                details={'reason': 'User not found during password update.'}
            )
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating password for user '{username}': {e}", exc_info=True)
        log_audit_event(
            action_type=ACTION_USER_PASSWORD_UPDATE_FAILED, outcome='FAILURE',
            username=username,
            details={'reason': f'Database error: {e}'}
        )
        return False
    finally:
        if conn:
            conn.close()

def delete_user(username: str) -> bool:
    """Deletes a user by username."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"User '{username}' deleted successfully.")
            log_audit_event(
                action_type=ACTION_USER_DELETED, outcome='SUCCESS',
                username=username,
                details={'message': 'User account deleted.'}
            )
            return True
        else:
            logger.warning(f"Failed to delete user '{username}': User not found.")
            log_audit_event(
                action_type=ACTION_USER_DELETE_FAILED, outcome='FAILURE',
                username=username,
                details={'reason': 'User not found during delete operation.'}
            )
            return False
    except sqlite3.Error as e:
        logger.error(f"Error deleting user '{username}': {e}", exc_info=True)
        log_audit_event(
            action_type=ACTION_USER_DELETE_FAILED, outcome='FAILURE',
            username=username,
            details={'reason': f'Database error: {e}'}
        )
        return False
    finally:
        if conn:
            conn.close()

def list_users() -> list[dict]:
    """Lists all users (excluding hashed_password for general listing)."""
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, created_at FROM users")
        users = [dict(row) for row in cursor.fetchall()]
        return users
    except sqlite3.Error as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

# --- User Authentication ---
def login_user(username: str, plain_password: str) -> dict or None:
    """
    Authenticates a user.
    Returns user details (excluding password) on success, None on failure.
    """
    user = get_user_by_username(username) # This function itself does not log audit events
    if user and verify_password(plain_password, user['hashed_password']):
        log_audit_event(
            action_type=ACTION_USER_LOGIN_SUCCESS, outcome='SUCCESS',
            user_id=user['id'], username=user['username'],
            details={'message': 'User logged in successfully.'}
        )
        return { # Return user info, excluding the hashed password for security
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "created_at": str(user["created_at"])
        }

    reason = 'Incorrect password.' if user else 'User not found.'
    log_audit_event(
        action_type=ACTION_USER_LOGIN_FAILURE, outcome='FAILURE',
        username=username, # Attempted username
        details={'reason': reason}
    )
    logger.warning(f"Login failed for user '{username}'. {reason}")
    return None


# --- RBAC (Role-Based Access Control) ---
ROLES_PERMISSIONS = {
    'admin': ['manage_users', 'run_pipelines', 'create_edit_pipelines', 'view_data', 'access_settings'],
    'editor': ['run_pipelines', 'create_edit_pipelines', 'view_data'],
    'viewer': ['view_data'],
    'user': ['view_data', 'run_pipelines'] # Default 'user' role permissions
}

def has_permission(user_role: str, required_permission: str) -> bool:
    """
    Checks if a user role has a specific permission.
    """
    if not user_role: # Handle cases like None or empty string for role
        return False
    user_permissions = ROLES_PERMISSIONS.get(user_role, [])
    return required_permission in user_permissions


# --- Initialize DB when module is loaded ---
if __name__ == "__main__":
    logger.info("Running user_management.py directly for testing/example with bcrypt.")
    init_db()

    # Clean up existing test users
    delete_user("testuser_bcrypt")
    delete_user("admin_bcrypt")

    logger.info("\n--- Testing add_user (with bcrypt) ---")
    add_user("testuser_bcrypt", "securepass123", "user")
    add_user("admin_bcrypt", "verysecureadminpass", "admin")

    logger.info("\n--- Testing get_user_by_username (bcrypt hashes are long) ---")
    user_b = get_user_by_username("testuser_bcrypt")
    logger.info(f"Fetched testuser_bcrypt (full data): {user_b}")

    logger.info("\n--- Testing login_user ---")
    login_success = login_user("testuser_bcrypt", "securepass123")
    logger.info(f"Login attempt for 'testuser_bcrypt' with correct password: {login_success}")
    assert login_success is not None and login_success['username'] == 'testuser_bcrypt'

    login_fail_pass = login_user("testuser_bcrypt", "wrongpassword")
    logger.info(f"Login attempt for 'testuser_bcrypt' with incorrect password: {login_fail_pass}")
    assert login_fail_pass is None

    login_fail_user = login_user("nonexistentuser", "anypassword")
    logger.info(f"Login attempt for 'nonexistentuser': {login_fail_user}")
    assert login_fail_user is None

    logger.info("\n--- Testing update_user_password (with bcrypt) ---")
    update_user_password("testuser_bcrypt", "newsecurepass456")

    logger.info("Re-fetching user to check new password...")
    user_b_new_pass_data = get_user_by_username("testuser_bcrypt") # Get full data with new hash
    if user_b_new_pass_data:
         logger.info(f"Verification for 'newsecurepass456' (should be True): {verify_password('newsecurepass456', user_b_new_pass_data['hashed_password'])}")
         logger.info(f"Verification for old 'securepass123' (should be False): {verify_password('securepass123', user_b_new_pass_data['hashed_password'])}")

    login_after_pass_change = login_user("testuser_bcrypt", "newsecurepass456")
    logger.info(f"Login attempt for 'testuser_bcrypt' with new password: {login_after_pass_change}")
    assert login_after_pass_change is not None

    login_with_old_pass = login_user("testuser_bcrypt", "securepass123")
    logger.info(f"Login attempt for 'testuser_bcrypt' with old password (should fail): {login_with_old_pass}")
    assert login_with_old_pass is None

    logger.info("\n--- Testing list_users (bcrypt) ---")
    all_users_bcrypt = list_users()
    logger.info(f"All users: {all_users_bcrypt}")
    for u in all_users_bcrypt:
        assert 'hashed_password' not in u

    # Clean up
    delete_user("testuser_bcrypt")
    delete_user("admin_bcrypt")

    logger.info("\n--- Testing RBAC has_permission ---")
    logger.info(f"Admin has 'manage_users': {has_permission('admin', 'manage_users')}") # True
    logger.info(f"Editor has 'manage_users': {has_permission('editor', 'manage_users')}") # False
    logger.info(f"Viewer has 'view_data': {has_permission('viewer', 'view_data')}") # True
    logger.info(f"Viewer has 'run_pipelines': {has_permission('viewer', 'run_pipelines')}") # False
    logger.info(f"User has 'run_pipelines': {has_permission('user', 'run_pipelines')}") # True
    logger.info(f"NonExistentRole has 'view_data': {has_permission('nonexistent', 'view_data')}") # False
    logger.info(f"Admin has 'nonexistent_perm': {has_permission('admin', 'nonexistent_perm')}") # False
    logger.info(f"None role has 'view_data': {has_permission(None, 'view_data')}") # False


    logger.info("Example usage with bcrypt finished.")
else:
    init_db()
