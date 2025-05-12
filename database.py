import sqlite3
import time # For Unix timestamps

DATABASE_FILE = 'chat_app.db'

def add_user(username, password):
    """Adds a new user to the database with a password."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()


        current_time = int(time.time())

        cursor.execute("INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)", 
                       (username, password, current_time))
        conn.commit()
        print(f"User '{username}' added successfully.")
        return True # Indicate success
    except sqlite3.IntegrityError:
        # This error likely means the username is already taken (due to UNIQUE constraint)
        print(f"Error: Username '{username}' already exists.")
        return False # Indicate failure (username taken)
    except sqlite3.Error as e:
        print(f"Database error adding user: {e}")
        return False # Indicate general failure
    finally:
        if conn:
            conn.close()

def get_user(username):
    """Retrieves user details by username."""
    conn = None
    user_data = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        # Use row_factory to get results as dictionary-like objects
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, username, password FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone() # Fetches one row or None

    except sqlite3.Error as e:
        print(f"Database error getting user: {e}")
    finally:
        if conn:
            conn.close()
    return user_data # Returns a Row object (like a dict) or None

def check_user_credentials(username, password):
    """Checks if the username exists and the password is correct."""
    user_data = get_user(username)
    if user_data:
        # Check the password
        stored_password = user_data['password']
        if stored_password == password:
            print(f"Password match for user '{username}'.")
            return user_data['user_id'] # Return user_id on success
        else:
            print(f"Password mismatch for user '{username}'.")
            return None # Password incorrect
    else:
        print(f"User '{username}' not found.")
        return None # User not found


def initialize_database():
    """Connects to the SQLite database and creates tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print("Database connection established.")

        # Enable Foreign Keys 
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );
        """)
        print("Checked/Created 'users' table.")

        # Create servers table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            server_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            admin_user_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (admin_user_id) REFERENCES users(user_id) ON DELETE CASCADE 
        );
        """)
        print("Checked/Created 'servers' table.")

        # Create memberships table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memberships (
            membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            joined_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE,
            UNIQUE(user_id, server_id) 
        );
        """)
        print("Checked/Created 'memberships' table.")

        # Create messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL 
        );
        """)
        print("Checked/Created 'messages' table.")

        # Create challenges table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            challenger_user_id INTEGER NOT NULL,
            admin_user_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'declined', 'in_progress', 'completed')), -- Example statuses
            winner_user_id INTEGER, -- Can be NULL
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (challenger_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (admin_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (winner_user_id) REFERENCES users(user_id) ON DELETE SET NULL -- If winner deleted, just remove winner ref
        );
        """)
        print("Checked/Created 'challenges' table.")

        conn.commit() # Save the changes (table creations)
        print("Database initialized successfully.")

    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed after initialization.")
