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
    """
    Removes a user from a server's membership list.
    If the user leaving is the admin:
    - If other members exist, the oldest remaining member becomes the new admin.
    - If the admin is the last member, the server is deleted.
    Returns:
        "SUCCESS_LEFT": User (non-admin) left successfully.
        "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED": Admin left, new admin assigned.
        "SUCCESS_ADMIN_LEFT_SERVER_DELETED": Admin left, server was empty and now deleted.
        "NOT_MEMBER": User was not a member of the server.
        "SERVER_NOT_FOUND": The specified server does not exist.
        "NOT_ADMIN_NO_SPECIAL_ACTION": User left, but was not admin, so no special admin logic.
        "ERROR": General database error or failed to assign new admin when expected.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        # Get current admin of the server
        cursor.execute("SELECT admin_user_id FROM servers WHERE server_id = ?", (server_id,))
        server_row = cursor.fetchone()

        if not server_row:
            print(f"Server ID {server_id} not found.")
            return "SERVER_NOT_FOUND"
        
        current_admin_id = server_row[0]
        is_leaving_user_admin = (user_id_leaving == current_admin_id)

        # Attempt to remove the user from memberships
        cursor.execute("DELETE FROM memberships WHERE user_id = ? AND server_id = ?", (user_id_leaving, server_id))
        
        if cursor.rowcount == 0:
            print(f"User ID {user_id_leaving} was not a member of server ID {server_id}.")
            # No change made to memberships, so no further admin logic needed even if they were listed as admin
            # (though this implies an inconsistency if they were admin but not in memberships).
            conn.rollback() # Rollback as no effective change intended if not a member
            return "NOT_MEMBER"

        # If the leaving user was NOT the admin, the job is simpler
        if not is_leaving_user_admin:
            conn.commit()
            print(f"User ID {user_id_leaving} (non-admin) removed from server ID {server_id}.")
            return "SUCCESS_LEFT"

        # --- If the leaving user WAS the admin, apply special logic ---
        print(f"Admin ID {user_id_leaving} is leaving server ID {server_id}. Applying special logic.")

        # Count remaining members
        cursor.execute("SELECT COUNT(*) FROM memberships WHERE server_id = ?", (server_id,))
        remaining_members_count = cursor.fetchone()[0]
        print(f"Remaining members in server {server_id}: {remaining_members_count}")

        if remaining_members_count > 0:
            # Promote the oldest remaining member
            # Using membership_id as a tie-breaker for joined_at ensures determinism
            cursor.execute("""
                SELECT user_id FROM memberships 
                WHERE server_id = ? 
                ORDER BY joined_at ASC, membership_id ASC 
                LIMIT 1
            """, (server_id,))
            new_admin_row = cursor.fetchone()

            if new_admin_row:
                new_admin_user_id = new_admin_row[0]
                cursor.execute("UPDATE servers SET admin_user_id = ? WHERE server_id = ?", 
                               (new_admin_user_id, server_id))
                conn.commit()
                print(f"Admin ID {user_id_leaving} left server ID {server_id}. New admin is User ID {new_admin_user_id}.")
                return "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED"
            else:
                # This case should ideally not be reached if remaining_members_count > 0.
                # It implies an issue or a very specific edge case.
                # To be safe, if no new admin can be found, consider it an error or delete the server.
                # For now, let's treat as an error as server should not be admin-less with members.
                conn.rollback() # Rollback changes as we couldn't assign a new admin
                print(f"ERROR: Server ID {server_id} has {remaining_members_count} members but could not find a new admin.")
                return "ERROR_FAILED_TO_ASSIGN_NEW_ADMIN"
        else:
            # Admin was the last member, delete the server
            cursor.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
            conn.commit()
            print(f"Admin ID {user_id_leaving} left server ID {server_id}. Server was empty and has been deleted.")
            return "SUCCESS_ADMIN_LEFT_SERVER_DELETED"

    except sqlite3.Error as e:
        print(f"Database error processing user {user_id_leaving} leaving server {server_id}: {e}")
        if conn:
            conn.rollback() # Rollback on any SQL error
        return "ERROR"
    finally:
        if conn:
            conn.close()

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
