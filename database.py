import sqlite3
import time # For Unix timestamps

SUPER_USER_ID = 1
SUPER_USER_USERNAME = "SYSTEM"
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

# --- Server Management Functions ---

def create_server(server_name, admin_user_id):
    """Creates a new server and makes the admin_user_id its first member."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;") # Ensure foreign key constraints are active
        
        current_time = int(time.time())
        
        # Insert into servers table
        cursor.execute("INSERT INTO servers (name, admin_user_id, created_at) VALUES (?, ?, ?)",
                       (server_name, admin_user_id, current_time))
        server_id = cursor.lastrowid 
        
        if server_id:
            # Add the admin as the first member of this new server
            cursor.execute("INSERT INTO memberships (user_id, server_id, joined_at) VALUES (?, ?, ?)",
                           (admin_user_id, server_id, current_time))
            conn.commit()
            print(f"Server '{server_name}' created with ID {server_id} and admin ID {admin_user_id}.")
            return server_id
        else:
            # This case (server_id is None after successful INSERT) is unlikely with AUTOINCREMENT
            # but good to handle defensively.
            conn.rollback()
            print(f"Failed to get server_id for new server '{server_name}'.")
            return None

    except sqlite3.IntegrityError as e:
        # e.g., if server names were UNIQUE and a duplicate was attempted.
        # Or if admin_user_id doesn't exist (though FK constraint should catch this if user is deleted)
        print(f"Database integrity error creating server '{server_name}': {e}")
        if conn:
            conn.rollback()
        return None
    except sqlite3.Error as e:
        print(f"Database error creating server '{server_name}': {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_all_servers():
    """Retrieves a list of all servers (id, name, admin_id)."""
    conn = None
    servers_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # Fetch admin username along with server details
        cursor.execute("""
            SELECT s.server_id, s.name, s.admin_user_id, u.username as admin_username
            FROM servers s
            JOIN users u ON s.admin_user_id = u.user_id
            ORDER BY s.name ASC
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            servers_list.append({
                "server_id": row["server_id"], 
                "name": row["name"], 
                "admin_user_id": row["admin_user_id"],
                "admin_username": row["admin_username"]
            })
            
    except sqlite3.Error as e:
        print(f"Database error retrieving all servers: {e}")
    finally:
        if conn:
            conn.close()
    return servers_list

def get_user_servers(user_id):
    """Retrieves a list of servers a specific user is a member of."""
    conn = None
    user_servers_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Joins servers, memberships, and users (for admin username)
        cursor.execute("""
            SELECT s.server_id, s.name, s.admin_user_id, u_admin.username as admin_username
            FROM servers s
            JOIN memberships m ON s.server_id = m.server_id
            JOIN users u_admin ON s.admin_user_id = u_admin.user_id
            WHERE m.user_id = ?
            ORDER BY s.name ASC
        """, (user_id,))
        rows = cursor.fetchall()
        
        for row in rows:
            user_servers_list.append({
                "server_id": row["server_id"],
                "name": row["name"],
                "admin_user_id": row["admin_user_id"],
                "admin_username": row["admin_username"]
            })
            
    except sqlite3.Error as e:
        print(f"Database error retrieving servers for user {user_id}: {e}")
    finally:
        if conn:
            conn.close()
    return user_servers_list

def add_user_to_server(user_id, server_id):
    """Adds a user to a server's membership list if they are not already a member."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")
        current_time = int(time.time())
        
        cursor.execute("INSERT INTO memberships (user_id, server_id, joined_at) VALUES (?, ?, ?)",
                       (user_id, server_id, current_time))
        conn.commit()
        print(f"User ID {user_id} added to server ID {server_id}.")
        return True
    except sqlite3.IntegrityError:
        # This will trigger if the (user_id, server_id) UNIQUE constraint is violated (already a member)
        # or if user_id/server_id does not exist (FK constraint violation)
        print(f"User ID {user_id} could not be added to server ID {server_id} (already a member or invalid ID).")
        return False
    except sqlite3.Error as e:
        print(f"Database error adding user {user_id} to server {server_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

def remove_user_from_server(user_id_leaving, server_id):
    conn = None # Initialize conn
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        cursor.execute("SELECT admin_user_id FROM servers WHERE server_id = ?", (server_id,))
        server_row = cursor.fetchone()
        if not server_row: return {"status": "SERVER_NOT_FOUND"}
        current_admin_id = server_row[0]
        is_leaving_user_admin = (user_id_leaving == current_admin_id)

        cursor.execute("DELETE FROM memberships WHERE user_id = ? AND server_id = ?", (user_id_leaving, server_id))
        if cursor.rowcount == 0:
            conn.rollback()
            return {"status": "NOT_MEMBER"}

        if not is_leaving_user_admin:
            conn.commit()
            return {"status": "SUCCESS_LEFT"}

        # Admin is leaving
        cursor.execute("SELECT COUNT(*) FROM memberships WHERE server_id = ?", (server_id,))
        remaining_members_count = cursor.fetchone()[0]

        if remaining_members_count > 0:
            cursor.execute("""
                SELECT u.user_id, u.username FROM memberships m
                JOIN users u ON m.user_id = u.user_id
                WHERE m.server_id = ? 
                ORDER BY m.joined_at ASC, m.membership_id ASC 
                LIMIT 1
            """, (server_id,))
            new_admin_data_row = cursor.fetchone() # Will be a tuple (user_id, username)

            if new_admin_data_row:
                new_admin_user_id = new_admin_data_row[0]
                new_admin_username = new_admin_data_row[1]
                cursor.execute("UPDATE servers SET admin_user_id = ? WHERE server_id = ?", 
                               (new_admin_user_id, server_id))
                conn.commit()
                return {
                    "status": "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED",
                    "data": {"new_admin_id": new_admin_user_id, "new_admin_username": new_admin_username}
                }
            else:
                conn.rollback()
                return {"status": "ERROR_FAILED_TO_ASSIGN_NEW_ADMIN"}
        else:
            cursor.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
            conn.commit()
            return {"status": "SUCCESS_ADMIN_LEFT_SERVER_DELETED"}
    except sqlite3.Error as e:
        print(f"Database error processing user {user_id_leaving} leaving server {server_id}: {e}")
        if conn: conn.rollback()
        return {"status": "ERROR", "data": {"details": str(e)}}
    finally:
        if conn: conn.close()

def get_server_details(server_id):
    """Retrieves details for a specific server, including admin username."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.server_id, s.name, s.admin_user_id, u.username as admin_username, s.created_at
            FROM servers s
            JOIN users u ON s.admin_user_id = u.user_id
            WHERE s.server_id = ?
        """, (server_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row) # Convert sqlite3.Row to a dictionary
        else:
            return None # Server not found
            
    except sqlite3.Error as e:
        print(f"Database error retrieving details for server {server_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def is_user_member(user_id, server_id):
    """Checks if a user is a member of a specific server."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM memberships WHERE user_id = ? AND server_id = ? LIMIT 1", (user_id, server_id))
        return cursor.fetchone() is not None # True if a row is found, False otherwise
            
    except sqlite3.Error as e:
        print(f"Database error checking membership for user {user_id} in server {server_id}: {e}")
        return False # Default to False on error
    finally:
        if conn:
            conn.close()

def get_server_members(server_id):
    """Retrieves a list of members (user_id, username) for a specific server."""
    conn = None
    members_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.user_id, u.username
            FROM users u
            JOIN memberships m ON u.user_id = m.user_id
            WHERE m.server_id = ?
            ORDER BY u.username ASC
        """, (server_id,))
        rows = cursor.fetchall()
        
        for row in rows:
            members_list.append(dict(row))
            
    except sqlite3.Error as e:
        print(f"Database error retrieving members for server {server_id}: {e}")
    finally:
        if conn:
            conn.close()
    return members_list

def add_message(server_id, user_id, content):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        current_time = int(time.time())
        cursor.execute("""
            INSERT INTO messages (server_id, user_id, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (server_id, user_id, content, current_time))
        conn.commit()
        message_id = cursor.lastrowid
        print(f"Message from UserID {user_id} saved to ServerID {server_id} with MsgID {message_id}.")
        return message_id # Return the new message's ID
    except sqlite3.Error as e:
        print(f"Database error adding message: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_messages_for_server(server_id, limit=50):
    conn = None
    messages_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.message_id, m.server_id, m.user_id, u.username as sender_username, m.content, m.timestamp
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.server_id = ?
            ORDER BY m.timestamp DESC 
            LIMIT ?
        """, (server_id, limit)) # Get latest N messages
        rows = cursor.fetchall()
        for row in reversed(rows): # Reverse to get them in chronological order for display
            messages_list.append(dict(row))
    except sqlite3.Error as e:
        print(f"Database error retrieving messages for server {server_id}: {e}")
    finally:
        if conn:
            conn.close()
    return messages_list

def initialize_database():
    """Connects to the SQLite database and creates tables and system user if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print("Database connection established.")
        cursor.execute("PRAGMA foreign_keys = ON;")

        # ... (your existing table creation statements for users, servers, memberships, messages, challenges) ...

        # Create the SYSTEM user (superuser)
        # Generate a dummy hash; this user should not be able to log in normally.
        dummy_password = "cannot_login_system_user_!@#$%^"
        current_time = int(time.time())

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
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, password, created_at) 
            VALUES (?, ?, ?, ?)
        """, (SUPER_USER_ID, SUPER_USER_USERNAME, dummy_password, current_time))
        if cursor.rowcount > 0:
            print(f"SYSTEM user '{SUPER_USER_USERNAME}' with ID {SUPER_USER_ID} created or ensured.")
        else:
            # Check if it exists with the correct username if ID was ignored due to PK conflict
            cursor.execute("SELECT username FROM users WHERE user_id = ?", (SUPER_USER_ID,))
            row = cursor.fetchone()
            if row and row[0] == SUPER_USER_USERNAME:
                print(f"SYSTEM user '{SUPER_USER_USERNAME}' (ID: {SUPER_USER_ID}) already exists.")
            else:
                print(f"WARNING: SYSTEM user with ID {SUPER_USER_ID} might exist with a different username, or insert failed for other reasons.")


        conn.commit()
        print("Database initialized successfully (including SYSTEM user check).")


    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed after initialization.")
