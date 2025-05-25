import sqlite3
import time # For Unix timestamps
import secrets

SUPER_USER_ID = 1
SUPER_USER_USERNAME = "SYSTEM"
DATABASE_FILE = 'chat_app.db'

def generate_invite_code(length = 12):
    return secrets.token_urlsafe(length)[:length]

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

def get_challenge_participants(challenge_id):
    """Retrieves a list of participants (user_id, username) for a given challenge."""
    conn = None
    participants = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, u.username 
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            WHERE cp.challenge_id = ?
            ORDER BY cp.joined_at ASC
        """, (challenge_id,))
        rows = cursor.fetchall()
        for row in rows:
            participants.append(dict(row))
    except sqlite3.Error as e:
        print(f"DB ERROR getting challenge participants for challenge_id {challenge_id}: {e}")
    finally:
        if conn:
            conn.close()
    return participants

def update_challenge_status(challenge_id, new_status):
    """Updates the status of a challenge and its updated_at timestamp."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")
        current_time = int(time.time())
        
        cursor.execute("""
            UPDATE challenges 
            SET status = ?, updated_at = ?
            WHERE challenge_id = ? 
        """, (new_status, current_time, challenge_id))
        
        if cursor.rowcount == 0:
            print(f"DB: No challenge found with ID {challenge_id} to update status to {new_status}.")
            conn.rollback() # Nothing was updated
            return False
            
        conn.commit()
        print(f"DB: Challenge ID {challenge_id} status updated to '{new_status}'.")
        return True
    except sqlite3.Error as e:
        print(f"DB ERROR updating challenge status for {challenge_id}: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def add_participant_to_challenge(challenge_id, user_id, max_participants=4):
    """
    Adds a user to a challenge if it's pending and not full.
    Returns:
        "SUCCESS": User added.
        "ALREADY_JOINED": User is already a participant.
        "CHALLENGE_FULL": Challenge has reached max participants.
        "CHALLENGE_NOT_PENDING": Challenge is not in 'pending' state.
        "CHALLENGE_NOT_FOUND": Challenge ID does not exist (should be caught by get_active_challenge earlier).
        "ERROR": Database error.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        # Check challenge status
        cursor.execute("SELECT status, challenger_user_id, admin_user_id FROM challenges WHERE challenge_id = ?", (challenge_id,))
        challenge_row = cursor.fetchone()
        if not challenge_row:
            return "CHALLENGE_NOT_FOUND" # Should be caught by get_active_challenge logic in server
        if challenge_row[0] != 'pending':
            return "CHALLENGE_NOT_PENDING"

        # Prevent admin or original challenger from re-joining via this mechanism
        if user_id == challenge_row[1] or user_id == challenge_row[2]:
            return "ALREADY_A_PRIMARY_PARTICIPANT" # Or some other suitable status

        # Check current number of participants
        current_participants = get_challenge_participants(challenge_id) # Uses a separate connection, or pass cursor
        if len(current_participants) >= max_participants:
            return "CHALLENGE_FULL"

        # Check if user is already a participant (UNIQUE constraint should also catch this)
        for p in current_participants:
            if p['user_id'] == user_id:
                return "ALREADY_JOINED"

        current_time = int(time.time())
        cursor.execute("""
            INSERT INTO challenge_participants (challenge_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (challenge_id, user_id, current_time))
        conn.commit()
        print(f"DB: User {user_id} added to challenge {challenge_id}.")
        return "SUCCESS"
    except sqlite3.IntegrityError: # Catches UNIQUE constraint violation
        print(f"DB: User {user_id} likely already joined challenge {challenge_id} (IntegrityError).")
        return "ALREADY_JOINED" # Should be caught by the explicit check above too
    except sqlite3.Error as e:
        print(f"DB ERROR adding participant to challenge {challenge_id}: {e}")
        if conn: conn.rollback()
        return "ERROR"
    finally:
        if conn:
            conn.close()

def create_challenge(server_id, challenger_user_id, admin_user_id):
    """
    Creates a new challenge in 'pending' status and adds challenger and admin as participants.
    Returns challenge_id on success, None on failure (e.g., active challenge already exists).
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        # Check for existing active (pending or accepted) challenges in this server
        cursor.execute("""
            SELECT challenge_id FROM challenges 
            WHERE server_id = ? AND status IN ('pending', 'accepted', 'in_progress')
        """, (server_id,))
        if cursor.fetchone():
            print(f"DB: Active challenge already exists for server_id {server_id}.")
            return None # Indicate active challenge exists

        current_time = int(time.time())
        cursor.execute("""
            INSERT INTO challenges (server_id, challenger_user_id, admin_user_id, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """, (server_id, challenger_user_id, admin_user_id, current_time, current_time))
        challenge_id = cursor.lastrowid

        if challenge_id:
            # Add initial challenger and admin to participants
            participants_to_add = [
                (challenge_id, challenger_user_id, current_time),
                (challenge_id, admin_user_id, current_time)
            ]
            cursor.executemany("""
                INSERT INTO challenge_participants (challenge_id, user_id, joined_at)
                VALUES (?, ?, ?)
            """, participants_to_add)

            conn.commit()
            print(f"DB: Challenge {challenge_id} created for server {server_id} by user {challenger_user_id} against admin {admin_user_id}.")
            return challenge_id
        else:
            conn.rollback()
            return None
    except sqlite3.Error as e:
        print(f"DB ERROR creating challenge: {e}")
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_active_challenge_for_server(server_id):
    """
    Retrieves details of an active ('pending', 'accepted', 'in_progress') challenge for a server.
    Returns a dictionary with challenge details or None.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM challenges 
            WHERE server_id = ? AND status IN ('pending', 'accepted', 'in_progress')
        """, (server_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB ERROR getting active challenge for server {server_id}: {e}")
        return None
    finally:
        if conn: conn.close()

def create_server(server_name, admin_user_id):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        current_time = int(time.time())

        # Generate a unique invite code
        invite_code = None
        while True:
            temp_code = generate_invite_code(12) 
            cursor.execute("SELECT 1 FROM servers WHERE invite_code = ?", (temp_code,))
            if cursor.fetchone() is None:
                invite_code = temp_code
                break # Found a unique code

        cursor.execute("""
            INSERT INTO servers (name, admin_user_id, created_at, invite_code) 
            VALUES (?, ?, ?, ?)
        """, (server_name, admin_user_id, current_time, invite_code))
        server_id = cursor.lastrowid

        if server_id:
            cursor.execute("INSERT INTO memberships (user_id, server_id, joined_at) VALUES (?, ?, ?)",
                           (admin_user_id, server_id, current_time))
            conn.commit()
            print(f"Server '{server_name}' (ID: {server_id}) created with invite code '{invite_code}' and admin ID {admin_user_id}.")
            return {"server_id": server_id, "invite_code": invite_code} # Return more info
        else:
            conn.rollback()
            return None
    # ... (rest of your except and finally blocks, ensure rollback on error) ...
    except sqlite3.Error as e: # Catch specific error
        print(f"Database error creating server '{server_name}': {e}")
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_server_by_invite_code(invite_code):
    """Retrieves server details by its invite code."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Join with users to get admin username as well
        cursor.execute("""
            SELECT s.server_id, s.name, s.admin_user_id, u.username as admin_username, s.invite_code
            FROM servers s
            JOIN users u ON s.admin_user_id = u.user_id
            WHERE s.invite_code = ?
        """, (invite_code,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            return None
    except sqlite3.Error as e:
        print(f"Database error retrieving server by invite code '{invite_code}': {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_invite_code_for_server(server_id):
    """Retrieves the invite code for a specific server."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT invite_code, name FROM servers WHERE server_id = ?", (server_id,))
        row = cursor.fetchone()
        if row:
            return {"invite_code": row[0], "server_name": row[1]}
        else:
            return None
    except sqlite3.Error as e:
        print(f"Database error retrieving invite code for server {server_id}: {e}")
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
    """Retrieves a list of servers a specific user is a member of, including invite codes."""
    conn = None
    user_servers_list = []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row # Allows accessing columns by name
        cursor = conn.cursor()
        
        # Modified SQL to include s.invite_code
        cursor.execute("""
            SELECT s.server_id, s.name, s.admin_user_id, u_admin.username as admin_username, s.invite_code
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
                "admin_username": row["admin_username"],
                "invite_code": row["invite_code"]  # <<< ADDED INVITE CODE HERE
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
            invite_code TEXT UNIQUE NOT NULL,
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

        # Create challenge_participants table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenge_participants (
            participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at INTEGER NOT NULL,
            FOREIGN KEY(challenge_id) REFERENCES challenges(challenge_id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(challenge_id, user_id) -- A user can only join a specific challenge once
        );
        """)
        print("Checked/Created 'challenge_participants' table.")

        # Create challenges table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            challenger_user_id INTEGER NOT NULL,
            admin_user_id INTEGER NOT NULL,
            extra_participant_1 INTEGER,
            extra_participant_2 INTEGER,
            status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'declined', 'in_progress', 'completed')), -- Example statuses
            winner_user_id INTEGER, -- Can be NULL
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE,
            FOREIGN KEY (challenger_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (admin_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (extra_participant_1) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (extra_participant_2) REFERENCES users(user_id) ON DELETE CASCADE,
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
