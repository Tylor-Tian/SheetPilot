import pytest
import sqlite3
from pathlib import Path
import bcrypt
import os # For managing test database file

# Functions to be tested
from app.core.user_management import (
    init_db,
    add_user,
    get_user_by_username,
    get_user_by_id,
    login_user,
    update_user_role,
    update_user_password,
    delete_user,
    list_users,
    hash_password,  # For testing hashing properties directly
    verify_password # For direct verification if needed in tests, though login_user covers it
)

# Original DATABASE_PATH from the module, to be patched
ORIGINAL_DB_PATH_MODULE_VAR = "app.core.user_management.DATABASE_PATH"
ORIGINAL_DB_DIR_MODULE_VAR = "app.core.user_management.DATABASE_DIR"


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """
    Pytest fixture to set up a temporary, isolated SQLite database for each test.
    - Creates a temporary database file.
    - Patches user_management.DATABASE_PATH to use this temporary file.
    - Calls init_db() to create the schema.
    - Yields the path to the temporary database.
    - Cleans up by ensuring the temporary database directory is removed by tmp_path.
    """
    temp_db_dir = tmp_path / ".sheetpilot_test"
    temp_db_dir.mkdir()
    temp_db_file = temp_db_dir / "test_user_data.db"

    # Patch the DATABASE_PATH and DATABASE_DIR in the user_management module
    monkeypatch.setattr(ORIGINAL_DB_PATH_MODULE_VAR, temp_db_file)
    monkeypatch.setattr(ORIGINAL_DB_DIR_MODULE_VAR, temp_db_dir)

    # Initialize the schema in the temporary database
    # init_db uses the patched DATABASE_PATH
    init_db()

    yield temp_db_file # Provide the path to the test function

    # Cleanup is handled by tmp_path fixture removing the directory
    # If we were not using tmp_path, we'd os.remove(temp_db_file) here.


# --- Test Cases ---

def test_add_user_success_and_get_user(test_db):
    """Test adding a user successfully and retrieving them."""
    assert add_user("testuser1", "password123", "user") is True

    user_by_name = get_user_by_username("testuser1")
    assert user_by_name is not None
    assert user_by_name["username"] == "testuser1"
    assert user_by_name["role"] == "user"

    # Verify password using bcrypt directly with the retrieved hash
    assert bcrypt.checkpw("password123".encode('utf-8'), user_by_name["hashed_password"].encode('utf-8'))

    user_by_id = get_user_by_id(user_by_name["id"])
    assert user_by_id is not None
    assert user_by_id["username"] == "testuser1"
    assert user_by_id["role"] == user_by_name["role"]
    assert user_by_id["hashed_password"] == user_by_name["hashed_password"]

def test_add_user_duplicate_username(test_db):
    """Test that adding a user with a duplicate username fails."""
    add_user("testuser2", "password123", "user")  # Add first user
    assert add_user("testuser2", "anotherpass", "admin") is False # Attempt duplicate

    # Verify only one user 'testuser2' exists and has the original role
    user = get_user_by_username("testuser2")
    assert user is not None
    assert user["role"] == "user"

def test_login_user_success(test_db):
    """Test successful login."""
    add_user("loginuser", "mypassword", "editor")

    logged_in_user = login_user("loginuser", "mypassword")
    assert logged_in_user is not None
    assert logged_in_user["username"] == "loginuser"
    assert logged_in_user["role"] == "editor"
    assert "hashed_password" not in logged_in_user # Ensure password hash isn't returned by login

def test_login_user_failure_wrong_password(test_db):
    """Test login failure with wrong password."""
    add_user("loginuser2", "correctpass", "user")
    assert login_user("loginuser2", "wrongpass") is None

def test_login_user_failure_user_not_found(test_db):
    """Test login failure with a username that does not exist."""
    assert login_user("nonexistentuser", "anypassword") is None

def test_update_user_role(test_db):
    """Test updating a user's role."""
    add_user("roleuser", "password", "user")
    assert update_user_role("roleuser", "admin") is True

    updated_user = get_user_by_username("roleuser")
    assert updated_user is not None
    assert updated_user["role"] == "admin"

    assert update_user_role("nonexistent_for_role_update", "admin") is False

def test_update_user_password(test_db):
    """Test updating a user's password."""
    username = "passuser"
    old_password = "oldpassword"
    new_password = "newpassword"

    add_user(username, old_password, "user")

    # Verify login with old password
    assert login_user(username, old_password) is not None

    # Update password
    assert update_user_password(username, new_password) is True

    # Login with old password should fail
    assert login_user(username, old_password) is None

    # Login with new password should succeed
    new_login_details = login_user(username, new_password)
    assert new_login_details is not None
    assert new_login_details["username"] == username

    assert update_user_password("nonexistent_for_pass_update", "new_pass") is False

def test_delete_user(test_db):
    """Test deleting a user."""
    username = "deleteuser"
    add_user(username, "password", "user")

    assert get_user_by_username(username) is not None # Exists before delete
    assert delete_user(username) is True

    assert get_user_by_username(username) is None # Does not exist after delete
    assert login_user(username, "password") is None # Cannot login after delete
    assert delete_user(username) is False # Deleting already deleted user

def test_list_users(test_db):
    """Test listing users."""
    users_to_add = [
        {"username": "listuser1", "password": "p1", "role": "user"},
        {"username": "listuser2", "password": "p2", "role": "admin"},
        {"username": "listuser3", "password": "p3", "role": "editor"},
    ]

    for u in users_to_add:
        add_user(u["username"], u["password"], u["role"])

    listed_users = list_users()
    assert len(listed_users) == len(users_to_add)

    # Check if usernames and roles match, and no passwords
    usernames_in_db = {u["username"] for u in listed_users}
    for u_add in users_to_add:
        assert u_add["username"] in usernames_in_db
        # Find the corresponding user in the list
        u_list_match = next((u_l for u_l in listed_users if u_l["username"] == u_add["username"]), None)
        assert u_list_match is not None
        assert u_list_match["role"] == u_add["role"]
        assert "hashed_password" not in u_list_match

def test_password_hashing_is_secure(test_db): # test_db fixture ensures bcrypt is available
    """Test properties of the bcrypt password hashing."""
    password = "myStrongPassword123!"

    hashed1 = hash_password(password)
    hashed2 = hash_password(password) # Hash same password again

    # 1. Original password should not be in the hash (obvious for bcrypt but good principle)
    assert password not in hashed1

    # 2. Two hashes of the same password should be different (due to different salts)
    assert hashed1 != hashed2

    # 3. Verification should work for both
    assert verify_password(password, hashed1) is True
    assert verify_password(password, hashed2) is True

    # 4. Verification should fail for wrong password
    assert verify_password("WrongPassword", hashed1) is False

def test_get_user_non_existent(test_db):
    """Test getting non-existent users by username and ID."""
    assert get_user_by_username("no_such_user") is None
    assert get_user_by_id(99999) is None

# Example of running tests:
# Ensure bcrypt is installed: pip install bcrypt
# pytest tests/test_user_management.py
