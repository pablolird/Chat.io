import sqlite3
import time # For Unix timestamps
# Consider adding password hashing library
# import bcrypt

DATABASE_FILE = 'chat_app.db'

def initialize_database():
    """Connects to the SQLite database and creates tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print("Database connection established.")

        # Enable Foreign Key support (important!)
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
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
            -- ON DELETE CASCADE means if the admin user is deleted, the server is also deleted. Adjust if needed.
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
            UNIQUE(user_id, server_id) -- Ensure a user can only join a server once
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
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE 
            -- Consider ON DELETE SET NULL for user_id if you want messages to remain after user deletion
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
