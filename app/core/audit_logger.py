import sqlite3
from pathlib import Path
import logging
import json
import datetime # For timestamp if not using SQL's CURRENT_TIMESTAMP directly in Python

# Configure logging for the audit logger itself (e.g., if DB write fails)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
AUDIT_DATABASE_DIR = Path.home() / ".sheetpilot" # Same directory as user_data.db
AUDIT_DATABASE_PATH = AUDIT_DATABASE_DIR / "audit_log.db"

# --- Standard Action Types ---
# User Management Actions
ACTION_USER_LOGIN_SUCCESS = "USER_LOGIN_SUCCESS"
ACTION_USER_LOGIN_FAILURE = "USER_LOGIN_FAILURE"
ACTION_USER_LOGOUT = "USER_LOGOUT" # Placeholder for future implementation
ACTION_USER_CREATED = "USER_CREATED_BY_ADMIN"
ACTION_USER_ROLE_UPDATED = "USER_ROLE_UPDATED_BY_ADMIN"
ACTION_USER_PASSWORD_UPDATED = "USER_PASSWORD_UPDATED_BY_ADMIN" # Or by user themselves
ACTION_USER_DELETED = "USER_DELETED_BY_ADMIN"
ACTION_USER_CREATE_FAILED = "USER_CREATE_FAILED"
ACTION_USER_ROLE_UPDATE_FAILED = "USER_ROLE_UPDATE_FAILED"
ACTION_USER_PASSWORD_UPDATE_FAILED = "USER_PASSWORD_UPDATE_FAILED" # If needed
ACTION_USER_DELETE_FAILED = "USER_DELETE_FAILED" # If needed


# Data Processing / Pipeline Actions
ACTION_PIPELINE_EXECUTION_START = "PIPELINE_EXECUTION_START"
ACTION_PIPELINE_EXECUTION_SUCCESS = "PIPELINE_EXECUTION_SUCCESS" # Kept for clarity, but will use ACTION_PIPELINE_EXECUTION_END
ACTION_PIPELINE_EXECUTION_FAILURE = "PIPELINE_EXECUTION_FAILURE" # Kept for clarity, but will use ACTION_PIPELINE_EXECUTION_END
ACTION_PIPELINE_EXECUTION_END = "PIPELINE_EXECUTION_END" # New, more generic end event
ACTION_DATA_IMPORT = "DATA_IMPORTED"
ACTION_DATA_EXPORT = "DATA_EXPORTED"
ACTION_PLUGIN_LLM_NORMALIZER_USED = "PLUGIN_LLM_NORMALIZER_USED"

# System/Admin Actions
ACTION_ADMIN_USER_CREATED = "ADMIN_USER_CREATED" # Generic, can be CLI or GUI
ACTION_ADMIN_USER_CREATE_FAILED = "ADMIN_USER_CREATE_FAILED"
ACTION_ADMIN_ACCESS_USER_MANAGEMENT = "ADMIN_ACCESS_USER_MANAGEMENT_DIALOG"
ACTION_ADMIN_INITIATED_USER_ADDITION = "ADMIN_INITIATED_USER_ADDITION"
ACTION_ADMIN_INITIATED_ROLE_UPDATE = "ADMIN_INITIATED_ROLE_UPDATE"
ACTION_ADMIN_INITIATED_USER_DELETION = "ADMIN_INITIATED_USER_DELETION"
# ACTION_ADMIN_INITIATED_PASSWORD_RESET = "ADMIN_INITIATED_PASSWORD_RESET" # For future
ACTION_AUDIT_DB_INIT_FAILURE = "AUDIT_DB_INIT_FAILURE" # Meta-action for audit system itself

def init_audit_db():
    """Initializes the audit log database and creates the audit_entries table."""
    conn = None
    try:
        AUDIT_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensuring audit database directory exists at: {AUDIT_DATABASE_DIR}")

        conn = sqlite3.connect(AUDIT_DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            username TEXT,
            action_type TEXT NOT NULL,
            details TEXT,
            outcome TEXT NOT NULL
        )
        """)

        conn.commit()
        logger.info(f"Audit database initialized and 'audit_entries' table ensured at: {AUDIT_DATABASE_PATH}")

    except sqlite3.Error as e:
        # Log critical error if audit DB can't be initialized
        logger.critical(f"CRITICAL: Audit database initialization error: {e}", exc_info=True)
        # Optionally, could try to log this failure to a fallback file log if DB is critical
    finally:
        if conn:
            conn.close()

def log_audit_event(action_type: str, outcome: str, user_id: int = None, username: str = None, details: dict = None):
    """
    Logs an audit event to the audit_entries table.

    Args:
        action_type (str): The type of action being logged (e.g., 'USER_LOGIN').
        outcome (str): The result of the action (e.g., 'SUCCESS', 'FAILURE', 'INFO').
        user_id (int, optional): The ID of the user performing the action. Defaults to None.
        username (str, optional): The username of the user performing the action. Defaults to None.
        details (dict, optional): A dictionary containing additional context/parameters for the event.
                                  Will be stored as a JSON string. Defaults to None.
    """
    conn = None
    try:
        details_json = json.dumps(details) if details is not None else None

        conn = sqlite3.connect(AUDIT_DATABASE_PATH)
        cursor = conn.cursor()

        # Using Python's datetime for timestamp to ensure consistency if CURRENT_TIMESTAMP is tricky across DBs/tests
        # However, SQLite's DEFAULT CURRENT_TIMESTAMP is generally reliable.
        # For this implementation, we'll rely on the table's default for timestamp.
        cursor.execute(
            """
            INSERT INTO audit_entries (user_id, username, action_type, details, outcome)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, username, action_type, details_json, outcome)
        )
        conn.commit()
        # logger.debug(f"Audit event logged: {action_type}, Outcome: {outcome}, User: {username or user_id}")

    except sqlite3.Error as e:
        logger.error(f"Failed to log audit event to SQLite DB: {e}", exc_info=True)
        logger.error(f"Original event details - Action: {action_type}, Outcome: {outcome}, User: {username}, Details: {details}")
    except json.JSONDecodeError as je:
        logger.error(f"Failed to serialize audit event details to JSON: {je}", exc_info=True)
        logger.error(f"Original event details (serialization failed) - Action: {action_type}, Outcome: {outcome}, User: {username}, Details: {details}")
    except Exception as ex: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred while logging audit event: {ex}", exc_info=True)
        logger.error(f"Original event details (unexpected error) - Action: {action_type}, Outcome: {outcome}, User: {username}, Details: {details}")
    finally:
        if conn:
            conn.close()

# --- Initialize Audit DB when module is loaded ---
# This ensures the DB and table are ready when other parts of the app import this module.
try:
    init_audit_db()
except Exception as e:
    # This is a fallback critical log. init_audit_db itself also logs.
    # This ensures that if init_audit_db raises an unhandled exception (e.g. due to permissions before even connecting)
    # it's caught and logged here at module load time.
    logger.critical(f"CRITICAL FAILURE during initial audit_logger.init_audit_db() call on module load: {e}", exc_info=True)
    # Attempt to log this critical failure into the (possibly non-functional) audit log itself, or a file.
    # Since the DB might be the issue, logging to it might fail.
    log_audit_event(
        action_type=ACTION_AUDIT_DB_INIT_FAILURE,
        outcome="CRITICAL_ERROR",
        details={"error": str(e), "message": "Audit DB initialization failed during module load."}
    )


if __name__ == "__main__":
    logger.info("Running audit_logger.py directly for testing/example.")

    # Test logging various events
    log_audit_event(ACTION_USER_LOGIN_SUCCESS, "SUCCESS", user_id=1, username="testadmin", details={"ip_address": "192.168.1.100"})
    log_audit_event(ACTION_USER_LOGIN_FAILURE, "FAILURE", username="unknownuser", details={"reason": "Invalid credentials", "ip_address": "10.0.0.5"})
    log_audit_event(ACTION_PIPELINE_EXECUTION_START, "INFO", user_id=2, username="editor_user", details={"pipeline_name": "sales_data_cleanup_v2", "input_file": "sales.csv"})
    log_audit_event(ACTION_PIPELINE_EXECUTION_SUCCESS, "SUCCESS", user_id=2, username="editor_user", details={"pipeline_name": "sales_data_cleanup_v2", "rows_processed": 10520})
    log_audit_event(ACTION_USER_CREATED, "SUCCESS", user_id=1, username="testadmin", details={"new_user_username": "newbie", "role_assigned": "viewer"})
    log_audit_event("CUSTOM_SYSTEM_EVENT", "INFO", details={"message": "System maintenance scheduled."})

    logger.info("Example audit logs created. Check 'audit_log.db'.")

    # Example of how to query and view logs (for manual inspection)
    try:
        conn_check = sqlite3.connect(AUDIT_DATABASE_PATH)
        cursor_check = conn_check.cursor()
        logger.info("\n--- Last 5 Audit Log Entries ---")
        for row in cursor_check.execute("SELECT * FROM audit_entries ORDER BY timestamp DESC LIMIT 5"):
            logger.info(dict(zip([column[0] for column in cursor_check.description], row)))
        conn_check.close()
    except Exception as e:
        logger.error(f"Failed to query audit log for example display: {e}")
