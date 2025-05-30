# SERVER.PY
# Refine Server-Specific Messaging
import socket
import threading
import os
import sys
import database # Your database module
import json
import pymongo
import time
import struct
import platform
import datetime
import subprocess # <<< ADDED
import select     # <<< ADDED
import fcntl      # <<< ADDED (Linux specific for non-blocking IO)


MSG_LENGTH_PREFIX_FORMAT = '!I'  # Network byte order, Unsigned Integer (4 bytes)
MSG_LENGTH_PREFIX_SIZE = struct.calcsize(MSG_LENGTH_PREFIX_FORMAT)
SUPERUSER_ID = 1
SUPERUSER_USERNAME = "SYSTEM"
CHALLENGE_USER_ID = 2
CHALLENGE_USER_USERNAME = "CHALLENGE_NOTICE"
MAX_CHALLENGE_PARTICIPANTS = 4
DUMMY_MINIGAME_IP = "127.0.0.1"
DUMMY_MINIGAME_PORT = 9999 # Example port
game_processes = {} # <<< ADDED: Tracks running games {challenge_id: process_object}
game_monitor_threads = {} # <<< ADDED: Tracks monitor threads {challenge_id: thread_object}


def detect_os():
    """Detects the operating system and returns its name."""
    return platform.system()

def is_windows():
    """Checks if the operating system is Windows."""
    return os.name == 'nt'

def get_godot_executable_path():
    """Returns the absolute path to the Godot executable based on the OS."""
    cwd = os.getcwd()
    godot_dir = os.path.join(cwd, "GodotGame")
    
    if is_windows():
        executable_name = "FinalWindows.exe"
    else:
        executable_name = "FinalLinux.x86_64"
    
    executable_path = os.path.join(godot_dir, executable_name)
    return executable_path

# Get the correct path
GODOT_EXECUTABLE_PATH = get_godot_executable_path()



try:
    # --- Check if the file exists before attempting to run ---
    if not os.path.exists(GODOT_EXECUTABLE_PATH):
        raise FileNotFoundError(f"Executable not found at {GODOT_EXECUTABLE_PATH}")
    
    # --- Check for execute permissions (optional but helpful for debugging) ---
    if not os.access(GODOT_EXECUTABLE_PATH, os.X_OK):
         print(f"WARNING: Executable at {GODOT_EXECUTABLE_PATH} might not have execute permissions.")

except FileNotFoundError:
    print(f"ERROR: Godot executable not found at {GODOT_EXECUTABLE_PATH}")
    # Make sure database.update_challenge_status is defined and working
    # database.update_challenge_status(challenge_id, "pending") # Revert status



try:
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017/") # Default local MongoDB URI

    log_db = mongo_client["chat_app_logs"] # Select or create a database named 'chat_app_logs'
    message_logs_collection = log_db["message_traffic"] # Select or create a collection

    print("Soy puto")
    # Test connection
    mongo_client.admin.command('ping')
    print("MongoDB connection successful. Logging is active.")
    mongodb_logging_active = True
except pymongo.errors.ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}. Logging will be disabled.")
    mongodb_logging_active = False
except Exception as e_mongo_init:
    print(f"An error occurred during MongoDB initialization: {e_mongo_init}. Logging will be disabled.")
    mongodb_logging_active = False

def log_to_mongodb(direction, client_addr, user_details, json_data):
    """Logs a JSON message to MongoDB."""
    if not mongodb_logging_active:
        return # Don't attempt to log if MongoDB isn't available

    try:
        log_entry = {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc), # Store as UTC
            "direction": direction,  # "SENT_TO_CLIENT" or "RECEIVED_FROM_CLIENT"
            "client_ip": client_addr[0] if client_addr else None,
            "client_port": client_addr[1] if client_addr else None,
            "user_id": user_details.get("user_id") if user_details else None,
            "username": user_details.get("username") if user_details else None,
            "message_json": json_data # Store the actual JSON object (or string if preferred)
        }
        message_logs_collection.insert_one(log_entry)
    except Exception as e:
        print(f"Error logging to MongoDB: {e}")

def receive_all(sock, num_bytes_to_receive):
    received_data = bytearray()
    while len(received_data) < num_bytes_to_receive:
        try:
            bytes_to_get_now = min(num_bytes_to_receive - len(received_data), 4096)
            packet = sock.recv(bytes_to_get_now)
        except socket.timeout:
            print(f"SERVER: Socket timeout during receive_all from {sock.getpeername()}.")
            return None
        except ConnectionAbortedError:
            print(f"SERVER: Connection aborted during receive_all from {sock.getpeername()}.")
            return None
        except Exception as e:
            print(f"SERVER: Socket error during receive_all from {sock.getpeername()}: {e}")
            return None

        if not packet:
            print(f"SERVER: Connection closed by {sock.getpeername()} while expecting more data in receive_all.")
            return None
        received_data.extend(packet)
    return received_data

def send_json(sock, data_dict, client_addr_for_log = None, user_details_for_log = None):
    try:
        if sock is None: return False # <<< ADDED: Check if socket is valid
        if mongodb_logging_active: # Check before calling log function
            log_to_mongodb("SENT_TO_CLIENT", client_addr_for_log, user_details_for_log, data_dict)
        json_bytes = json.dumps(data_dict).encode('utf-8')
        len_prefix = struct.pack(MSG_LENGTH_PREFIX_FORMAT, len(json_bytes))
        sock.sendall(len_prefix)
        sock.sendall(json_bytes)
        return True
    except BrokenPipeError:
        peer_name = "unknown peer"
        try:
            peer_name = sock.getpeername()
        except OSError: pass # Socket might already be closed/invalid
        print(f"SERVER: Broken pipe while sending to {peer_name}. Client likely disconnected.")
        return False
    except Exception as e:
        peer_name = "unknown peer"
        try:
            peer_name = sock.getpeername()
        except OSError: pass
        print(f"SERVER: Error sending JSON data to {peer_name}: {e}")
        # print(f"SERVER: Data that failed: {data_dict}") # Be cautious logging potentially large/sensitive data
        return False

def receive_json(sock):

    global running
    try:
        # 1. Receive the 4-byte length prefix
        len_prefix_bytes = receive_all(sock, MSG_LENGTH_PREFIX_SIZE)
        if len_prefix_bytes is None:
            return None

        # 2. Unpack the length prefix
        actual_message_length = struct.unpack(MSG_LENGTH_PREFIX_FORMAT, len_prefix_bytes)[0]
        print(f"SERVER DEBUG: Expecting JSON message of length: {actual_message_length} from {sock.getpeername()}")

        # Limit message size to prevent memory exhaustion attacks if necessary
        if actual_message_length > 10 * 1024 * 1024: # Example: 10MB limit
            print(f"SERVER WARNING: Message length {actual_message_length} exceeds limit from {sock.getpeername()}. Closing connection.")
            sock.close()
            return None

        # 3. Receive the actual JSON message data
        json_message_bytes = receive_all(sock, actual_message_length)
        if json_message_bytes is None:
            return None

        # 4. Decode and parse JSON
        json_string = json_message_bytes.decode('utf-8')
        print(f"SERVER DEBUG: Received JSON string: {json_string[:200]}... from {sock.getpeername()}")
        return json.loads(json_string)

    except struct.error as se:
        print(f"SERVER: Struct unpack error (bad length prefix or conn issue from {sock.getpeername()}): {se}")
        return None
    except json.JSONDecodeError as je:
        print(f"SERVER: Failed to decode JSON from {sock.getpeername()}. Error: {je}")
        print(f"SERVER DEBUG MALFORMED JSON DATA: <{json_message_bytes.decode('utf-8', errors='ignore') if 'json_message_bytes' in locals() else 'Could not decode for debug'}>")
        return {"status": "error", "message": "Malformed JSON received."} # Send an error JSON back if possible
    except Exception as e:
        print(f"SERVER: Critical error in receive_json from {sock.getpeername()}: {e}")
        return None # General error

def broadcast_message_to_server(username, user_id, server_id, server_name, message_text, response, client_socket):
    # Persist the message
    thread_name = threading.current_thread().name # Get current thread name for logging
    message_id = database.add_message(server_id, user_id, message_text)
    if message_id:
        chat_message_broadcast = {
            "type": "CHAT_MESSAGE",
            "payload": {
                "sender_username": username,
                "sender_user_id": user_id,
                "message": message_text,
                "timestamp": int(time.time()),
                "server_id": server_id,
                "server_name": server_name,
                "message_id": message_id
            }
        }
        print(f"DEBUG: [{thread_name}] Relaying message from {username} to server '{server_name}' (ID: {server_id})")

        # Broadcast to all online members of that specific server
        server_members = database.get_server_members(server_id)
        with lock:
            for member in server_members:
                member_id = member['user_id']
                if member_id in authenticated_clients: # Check if member is online
                    send_json(authenticated_clients[member_id]['socket'], chat_message_broadcast)

    else:
        response["message"] = "Failed to save your message."
        send_json(client_socket, response)

def broadcast_system_message_to_server(server_id, server_name, message_text, response, client_socket):
    thread_name = threading.current_thread().name # Get current thread name for logging
    print(f"DEBUG: [{thread_name}] Attempting to broadcast SYSTEM message to server_id {server_id} ('{server_name}'): {message_text}")
    message_id = database.add_message(server_id, SUPERUSER_ID, message_text)
    if message_id:
        chat_message_broadcast = {
            "type": "CHAT_MESSAGE", # Use the existing chat message type
                "payload": {
            "sender_username": SUPERUSER_USERNAME,
            "sender_user_id": SUPERUSER_ID,
            "message": message_text,
            "timestamp": int(time.time()),
            "server_id": server_id,
            "server_name": server_name,
            "message_id": message_id
            }
        }
        print(f"DEBUG: [{thread_name}] Relaying message from {SUPERUSER_USERNAME} to server '{server_name}' (ID: {server_id})")

        # Broadcast to all online members of that specific server
        server_members = database.get_server_members(server_id)
        with lock:
            for member in server_members:
                member_id = member['user_id']
                if member_id in authenticated_clients: # Check if member is online
                    # No need to check if member_id != self.user_id if client handles its own messages
                    send_json(authenticated_clients[member_id]['socket'], chat_message_broadcast)
        # No direct response to sender for SEND_CHAT_MESSAGE usually
    else:
        # Check if client_socket is valid before sending error
        if client_socket:
            response["message"] = "Failed to save your system message."
            send_json(client_socket, response)


def broadcast_challenge_message_to_server(server_id, server_name, message_text, response, client_socket):
    thread_name = threading.current_thread().name # Get current thread name for logging
    print(f"DEBUG: [{thread_name}] Attempting to broadcast SYSTEM message to server_id {server_id} ('{server_name}'): {message_text}")
    message_id = database.add_message(server_id, CHALLENGE_USER_ID, message_text)
    if message_id:
        chat_message_broadcast = {
            "type": "CHAT_MESSAGE", # Use the existing chat message type
                "payload": {
            "sender_username": CHALLENGE_USER_USERNAME,
            "sender_user_id": CHALLENGE_USER_ID,
            "message": message_text,
            "timestamp": int(time.time()),
            "server_id": server_id,
            "server_name": server_name,
            "message_id": message_id
            }
        }
        print(f"DEBUG: [{thread_name}] Relaying message from {SUPERUSER_USERNAME} to server '{server_name}' (ID: {server_id})")

        # Broadcast to all online members of that specific server
        server_members = database.get_server_members(server_id)
        with lock:
            for member in server_members:
                member_id = member['user_id']
                if member_id in authenticated_clients: # Check if member is online
                    # No need to check if member_id != self.user_id if client handles its own messages
                    send_json(authenticated_clients[member_id]['socket'], chat_message_broadcast)
        # No direct response to sender for SEND_CHAT_MESSAGE usually
    else:
        response["message"] = "Failed to save your message."
        send_json(client_socket, response)

def validate_membership(client_socket, response, user_id, server_details, target_server_id):
    if not server_details:
        response["message"] = f"Server ID {target_server_id} not found."
        send_json(client_socket, response)
        return False

    if not database.is_user_member(user_id, server_details['server_id']):
        response["message"] = f"You are not a member of server '{server_details['name']}'."
        send_json(client_socket, response)
        return False

    return True

def join_server(client_socket, response, user_id, username, invite_code_to_join):
    if invite_code_to_join:
        server_to_join = database.get_server_by_invite_code(invite_code_to_join)
        if server_to_join:
            server_id = server_to_join['server_id']
            server_name = server_to_join['name']
            if database.is_user_member(user_id, server_id):
                response["message"] = f"You are already a member of server '{server_name}'."
            else:
                # Broadcast system message about user joining this server
                broadcast_system_message_to_server(server_id, server_name, f"{username} joined the server.", response, client_socket)
                database.add_user_to_server(user_id, server_id)
                response["status"] = "success"
                response["message"] = f"Successfully joined server '{server_name}'!"
                response["data"] = {"server_id": server_id, "server_name": server_name}

        else:
            response["message"] = "Invalid invite code or server does not exist."
    else:
        response["message"] = "Invite code missing in payload for JOIN_SERVER."
    send_json(client_socket, response)
    return

# <<< ADDED: Function to monitor game process >>>
def monitor_game_process(challenge_id, process, server_id, server_name):
    """Monitors the stdout of a game server subprocess for the winner."""
    thread_name = threading.current_thread().name
    print(f"INFO: [{thread_name}] Starting monitor for Challenge ID: {challenge_id}, PID: {process.pid}")

    winner_username = None
    buffer = b'' # Use a buffer to store partial lines

    try:
        # Set stdout to non-blocking (Linux specific)
        fd = process.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        while process.poll() is None: # While process is running
            ready_to_read, _, _ = select.select([process.stdout], [], [], 1.0) # 1 sec timeout

            if ready_to_read:
                print("soy gay")
                try:
                    # Read available data (up to 4096 bytes), not just one line
                    chunk = process.stdout.read(4096)

                    if chunk is None:
                        # This is the condition we want to handle, though it's weird.
                        print(f"WARNING: [{thread_name}] process.stdout.read() returned None. Assuming EOF.")
                        break
                    if not chunk:
                        # This is the standard way to detect EOF.
                        print(f"INFO: [{thread_name}] process.stdout.read() returned b''. Assuming EOF.")
                        break

                    buffer += chunk # Add read data to our buffer

                    # Process all full lines currently in the buffer
                    while b'\n' in buffer:
                        line_bytes, buffer = buffer.split(b'\n', 1)
                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                        if line: # Process only non-empty lines
                            print(f"GAME_LOG (Challenge {challenge_id}): {line}")
                            if line.startswith("WINNER:"):
                                winner_username = line.split(":", 1)[1].strip()
                                print(f"INFO: [{thread_name}] Detected winner for Challenge {challenge_id}: {winner_username}")
                                # Optional: you could break here if you don't need further output

                except BlockingIOError:
                    # No data was *actually* available despite select (rare, but possible)
                    # or read() finished all available data. Just loop and wait for select again.
                    pass
                except Exception as e:
                    # Catch other potential reading errors
                    print(f"ERROR: [{thread_name}] Inner loop error reading stdout for Challenge {challenge_id}: {e}")
                    break # Exit on other errors too

            # Small sleep even if select times out, avoids 100% CPU if select behaves strangely.
            time.sleep(0.1)

    except Exception as e:
        print(f"ERROR: [{thread_name}] Outer loop error reading stdout for Challenge {challenge_id}: {e}")

    # Process any remaining data in the buffer after the process finishes
    if buffer:
        lines = buffer.split(b'\n')
        for line_bytes in lines:
            line = line_bytes.decode('utf-8', errors='ignore').strip()
            if line:
                 print(f"GAME_LOG (Challenge {challenge_id}, Final): {line}")
                 if line.startswith("WINNER:") and not winner_username:
                     winner_username = line.split(":", 1)[1].strip()
                     print(f"INFO: [{thread_name}] Detected winner (final) for Challenge {challenge_id}: {winner_username}")

    # --- Rest of the function (Process finished or error occurred) ---
    return_code = process.wait() # Ensure process is finished and get return code
    print(f"INFO: [{thread_name}] Game process for Challenge {challenge_id} finished. PID: {process.pid}, Code: {return_code}")

    # (Your existing winner processing logic here...)
    if winner_username:
        winner_user_id = database.get_user_by_name(winner_username)
        if winner_user_id:
            print(f"INFO: [{thread_name}] Processing winner {winner_username} (ID: {winner_user_id}) for Challenge {challenge_id}")
            database.update_challenge_status(challenge_id, "completed")
            database.add_winner_to_challenge(challenge_id, winner_user_id)
            if database.update_server_admin(server_id, winner_user_id):
                broadcast_system_message_to_server(
                    server_id, server_name,
                    f"Challenge {challenge_id} has ended! The winner and new admin is: {winner_username}!",
                    {}, None
                )
            else:
                broadcast_system_message_to_server(
                    server_id, server_name,
                    f"Challenge {challenge_id} has ended! Winner: {winner_username}. (Admin change failed).",
                    {}, None
                )
        else:
            print(f"ERROR: [{thread_name}] Could not find user_id for winner: {winner_username}. Challenge: {challenge_id}")
            database.update_challenge_status(challenge_id, "completed")
            broadcast_system_message_to_server(
                server_id, server_name,
                f"Challenge {challenge_id} ended, but winner ({winner_username}) could not be processed.",
                {}, None
            )
    else:
        print(f"WARNING: [{thread_name}] Game for Challenge {challenge_id} finished, but no winner was detected via stdout.")
        database.update_challenge_status(challenge_id, "completed")
        broadcast_system_message_to_server(
            server_id, server_name,
            f"Challenge {challenge_id} ended. No winner was determined.",
            {}, None
        )

    # Cleanup
    with lock: # Make sure 'lock' is accessible or passed if needed
        if challenge_id in game_processes:
            del game_processes[challenge_id]
        if challenge_id in game_monitor_threads:
            del game_monitor_threads[challenge_id]
    print(f"INFO: [{thread_name}] Monitor for Challenge {challenge_id} finished.")


# Global dictionary to store authenticated clients, keyed by user_id
# Each value will be a dictionary: {'socket': client_socket, 'username': username, 'addr': addr, 'current_server_id': None}
authenticated_clients = {}
lock = threading.Lock() # Lock for synchronizing access to authenticated_clients

class ClientThread(threading.Thread):
    def __init__(self, client_socket, addr, user_id, username):
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.user_id = user_id
        self.username = username
        self.running = True
        self.current_server_id = None # <<< ADDED for /users_in_server default

        thread_name = threading.current_thread().name
        print(f"DEBUG: [{thread_name}] ClientThread __init__ for UserID: {self.user_id}, Username: {self.username}, Addr: {self.addr}")
        with lock:
            authenticated_clients[self.user_id] = {
                'socket': self.client_socket,
                'username': self.username,
                'addr': self.addr,
            }
        print(f"DEBUG: [{thread_name}] User {self.username} (ID: {self.user_id}) added to authenticated_clients.")

    def run(self):
        thread_name = threading.current_thread().name
        print(f"DEBUG: [{thread_name}] ClientThread.run started for User: {self.username} (ID: {self.user_id})")

        join_broadcast = {
            "type": "USER_JOINED", # This is a global "joined the chat system" message
            "payload": {"username": self.username, "user_id": self.user_id, "timestamp": int(time.time())}
        }
        with lock:
            for target_user_id, client_info in authenticated_clients.items():
                if target_user_id != self.user_id:
                    send_json(client_info['socket'], join_broadcast)

        try:
            while self.running:
                print(f"DEBUG: [{thread_name}] ClientThread for User {self.username} waiting for JSON...")
                request_data = receive_json(self.client_socket)

                if request_data is None:
                    print(f"DEBUG: [{thread_name}] User {self.username} (ID: {self.user_id}) disconnected or bad data.")
                    self.running = False
                    break

                if mongodb_logging_active: # Check before calling log function
                    current_user_details = {"user_id": self.user_id, "username": self.username}
                    log_to_mongodb("RECEIVED_FROM_CLIENT", self.addr, current_user_details, request_data)

                print(f"DEBUG: [{thread_name}] Received from User {self.username}: {request_data}")

                action = request_data.get("action")
                payload = request_data.get("payload", {})
                response = {"action_response_to": action, "status": "error", "message": "Unhandled action or error."} # Default error response

                if action == "SEND_CHAT_MESSAGE":
                    server_id_target_str = payload.get("server_id")
                    message_content = payload.get("message")

                    if server_id_target_str is None or message_content is None:
                        response["message"] = "server_id and message are required for SEND_CHAT_MESSAGE."
                        send_json(self.client_socket, response)
                        continue

                    try:
                        target_server_id = int(server_id_target_str)

                        # Validate server and membership
                        server_details = database.get_server_details(target_server_id)
                        if (validate_membership(self.client_socket, response, self.user_id, server_details, target_server_id)):
                            # Persist the message
                            broadcast_message_to_server(self.username, self.user_id, target_server_id, server_details['name'], message_content, response, self.client_socket)
                            continue

                    except ValueError:
                        response["message"] = "Invalid server_id format for SEND_CHAT_MESSAGE."
                        send_json(self.client_socket, response)
                        continue

                elif action == "DISCONNECT":
                    print(f"DEBUG: [{thread_name}] User {self.username} sent DISCONNECT.")
                    self.running = False
                    # No response needed, client will close. Server closes in finally.
                    break

                elif action == "KICK_USER":
                    payload_server_id_str = payload.get("server_id")
                    payload_user_to_kick_id_str = payload.get("user_to_kick_id")

                    response = {"action_response_to": action, "status": "error", "message": "Default error for KICK_USER."}

                    if payload_server_id_str is None or payload_user_to_kick_id_str is None:
                        response["message"] = "server_id and user_to_kick_id are required."
                    else:
                        try:
                            target_server_id = int(payload_server_id_str)
                            user_to_kick_id = int(payload_user_to_kick_id_str)

                            server_details = database.get_server_details(target_server_id)

                            if not server_details:
                                response["message"] = f"Server ID {target_server_id} not found."
                            elif server_details['admin_user_id'] != self.user_id: # Check if requester is admin
                                response["message"] = "You are not the admin of this server and cannot kick users."
                            elif user_to_kick_id == self.user_id: # Admin trying to kick self
                                response["message"] = "Admins cannot kick themselves. Use /leave_server if you wish to leave."
                            elif user_to_kick_id == SUPERUSER_ID: # Trying to kick system user
                                response["message"] = "The SYSTEM user cannot be kicked."
                            elif not database.is_user_member(user_to_kick_id, target_server_id):
                                response["message"] = f"User ID {user_to_kick_id} is not a member of this server."
                            else:
                                kicked_user_details = database.get_user(user_to_kick_id) # To get username
                                kicked_username = kicked_user_details['username'] if kicked_user_details else f"User_{user_to_kick_id}"
                                removal_result = database.remove_user_from_server(user_to_kick_id, target_server_id)

                                if removal_result.get("status") == "SUCCESS_LEFT" or \
                                   removal_result.get("status") == "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED" or \
                                   removal_result.get("status") == "SUCCESS_ADMIN_LEFT_SERVER_DELETED":

                                    response["status"] = "success"
                                    response["message"] = f"User '{kicked_username}' (ID: {user_to_kick_id}) has been kicked from server '{server_details['name']}'."

                                    # Notify the server
                                    broadcast_system_message_to_server(
                                        target_server_id,
                                        server_details['name'],
                                        f"User '{kicked_username}' has been kicked from the server by Admin {self.username}.",
                                        response,
                                        self.client_socket
                                    )

                                    # Notify the kicked user if they are online
                                    with lock:
                                        if user_to_kick_id in authenticated_clients:
                                            kicked_user_socket = authenticated_clients[user_to_kick_id]['socket']
                                            kick_notification_to_user = {
                                                "type": "YOU_WERE_KICKED",
                                                "payload": {
                                                    "server_id": target_server_id,
                                                    "server_name": server_details['name'],
                                                    "kicked_by_username": self.username,
                                                    "timestamp": int(time.time())
                                                }
                                            }
                                            send_json(kicked_user_socket, kick_notification_to_user)
                                else:
                                    response["message"] = f"Failed to kick user '{kicked_username}'. Reason: {removal_result.get('status', 'Unknown error')}"
                                    if removal_result.get("status") == "NOT_MEMBER": # Should have been caught by is_user_member
                                         response["message"] = f"User '{kicked_username}' was not found as a member during removal."


                        except ValueError:
                            response["message"] = "Invalid server_id or user_to_kick_id format. Must be numbers."
                        except Exception as e_kick:
                            print(f"DEBUG: [{thread_name}] Exception in KICK_USER for {self.username}: {e_kick}")
                            response["message"] = f"An unexpected error occurred: {e_kick}"

                    send_json(self.client_socket, response) # Send response to the admin who issued kick
                    continue

                elif action == "ACCEPT_CHALLENGE":
                    server_id_str = payload.get("server_id")
                    response = {"action_response_to": action, "status": "error"}

                    if server_id_str is None:
                        response["message"] = "server_id is required to accept a challenge."
                    else:
                        try:
                            target_server_id = int(server_id_str)
                            server_details = database.get_server_details(target_server_id)

                            if not server_details:
                                response["message"] = f"Server ID {target_server_id} not found."
                            else:
                                server_name = server_details.get('name', f"ServerID_{target_server_id}")
                                active_challenge = database.get_active_challenge_for_server(target_server_id)

                                if not active_challenge:
                                    response["message"] = f"No active challenge found in server '{server_name}' to accept."
                                elif active_challenge.get('status') != 'pending':
                                    response["message"] = f"The challenge in server '{server_name}' is not 'pending' (current: {active_challenge.get('status')})."
                                elif self.user_id != active_challenge.get('admin_user_id'):
                                    response["message"] = "Only the challenged admin can accept this challenge."
                                elif active_challenge['challenge_id'] in game_processes:
                                     response["message"] = "A game for this challenge is already running or starting."
                                else:
                                    challenge_id = active_challenge['challenge_id']
                                    if database.update_challenge_status(challenge_id, "accepted"):
                                        response["status"] = "success"
                                        response["message"] = "Challenge accepted! Starting minigame server and sending invites..."

                                        # <<< START GAME SERVER SUBPROCESS >>>
                                        try:
                                            # <<< SEND INVITES >>>
                                            minigame_info_payload = {
                                                "challenge_id": challenge_id,
                                                "server_id": target_server_id,
                                                "server_name": server_name,
                                                "minigame_ip": DUMMY_MINIGAME_IP,
                                                "minigame_port": DUMMY_MINIGAME_PORT,
                                                "game_type": "DefaultMinigame"
                                            }
                                            participants = database.get_challenge_participants(challenge_id)
                                            participant_usernames = [p['username'] for p in participants]
                                            minigame_info_payload["all_participants"] = participant_usernames
                                            number_of_usernames = len(participant_usernames)
                                            print(number_of_usernames)
                                            if number_of_usernames == 4:
                                                player_number_flag = "--four"
                                            elif number_of_usernames == 3:
                                                player_number_flag = "--three"
                                            else:
                                                player_number_flag = ""
                                            game_command = [GODOT_EXECUTABLE_PATH, "--server", "--headless", f"--ip={DUMMY_MINIGAME_IP}", player_number_flag]
                                            print(f"DEBUG: Current Working Directory is: {os.getcwd()}") 
                                            print(f"INFO: [{thread_name}] Starting game server: {' '.join(game_command)}")
                                            game_proc = subprocess.Popen(
                                                game_command,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                                                text=False, # Read bytes
                                                bufsize=0, # Unbuffered
                                                cwd=os.path.dirname(GODOT_EXECUTABLE_PATH) or '.' # Run in GodotGame dir
                                            )
                                            with lock:
                                                game_processes[challenge_id] = game_proc
                                            print(f"INFO: [{thread_name}] Game server started for Challenge {challenge_id}. PID: {game_proc.pid}")

                                            # <<< START MONITOR THREAD >>>
                                            monitor_thread = threading.Thread(
                                                target=monitor_game_process,
                                                args=(challenge_id, game_proc, target_server_id, server_name),
                                                daemon=True # Allow server to exit even if monitor hangs
                                            )
                                            monitor_thread.start()
                                            with lock:
                                                game_monitor_threads[challenge_id] = monitor_thread

                                            # Give game server a moment to start (CRUDE!)
                                            time.sleep(2.0)

                                            with lock:
                                                for participant_data in participants:
                                                    p_user_id = participant_data['user_id']
                                                    if p_user_id in authenticated_clients:
                                                        send_json(authenticated_clients[p_user_id]['socket'], {
                                                            "type": "MINIGAME_INVITE",
                                                            "payload": minigame_info_payload
                                                        })

                                            broadcast_system_message_to_server(
                                                target_server_id, server_name,
                                                (f"Admin {self.username} accepted the challenge! "
                                                 f"Minigame starting for participants: {', '.join(participant_usernames)}."),
                                                response, self.client_socket
                                            )

                                        except FileNotFoundError:
                                            print(f"ERROR: [{thread_name}] Godot executable not found at {GODOT_EXECUTABLE_PATH}")
                                            response["status"] = "error"
                                            response["message"] = "Minigame server executable not found. Cannot start game."
                                            database.update_challenge_status(challenge_id, "pending") # Revert status
                                        except Exception as e_game_start:
                                            print(f"ERROR: [{thread_name}] Failed to start game server: {e_game_start}")
                                            response["status"] = "error"
                                            response["message"] = f"Failed to start minigame server: {e_game_start}"
                                            database.update_challenge_status(challenge_id, "pending") # Revert status
                                    else:
                                        response["message"] = "Failed to update challenge status in the database."
                        except ValueError:
                            response["message"] = "Invalid server_id format."
                        except Exception as e_accept_chal:
                            print(f"DEBUG: [{thread_name}] Exception in ACCEPT_CHALLENGE: {e_accept_chal}")
                            response["message"] = f"An unexpected error occurred: {e_accept_chal}"

                    send_json(self.client_socket, response)
                    continue


                elif action == "JOIN_CHALLENGE":
                    server_id_str = payload.get("server_id")
                    response = {"action_response_to": action, "status": "error", "message": "Default error joining challenge."} # Default error

                    if server_id_str is None:
                        response["message"] = "server_id is required to join a challenge."
                    else:
                        try:
                            target_server_id = int(server_id_str)
                            server_details = database.get_server_details(target_server_id) # Returns dict or None

                            if not server_details:
                                response["message"] = f"Server ID {target_server_id} not found."
                            elif not database.is_user_member(self.user_id, target_server_id): # Check if joiner is member of server
                                response["message"] = f"You are not a member of server '{server_details.get('name', 'Unknown Server')}'."
                            else:
                                # Safely get server name for messages
                                server_name = server_details.get('name', f"ServerID_{target_server_id}")

                                active_challenge = database.get_active_challenge_for_server(target_server_id) # Returns dict or None

                                if not active_challenge:
                                    response["message"] = f"No active challenge found in server '{server_name}' to join."
                                elif active_challenge.get('status') != 'pending': # Now safe to access 'status'
                                    response["message"] = (f"The challenge in server '{server_name}' is not currently 'pending' "
                                                           f"(current status: {active_challenge.get('status')}).")
                                elif self.user_id == active_challenge.get('admin_user_id') or \
                                     self.user_id == active_challenge.get('challenger_user_id'):
                                    response["message"] = "You are already a primary participant (admin or original challenger) in this challenge."
                                else:
                                    challenge_id = active_challenge['challenge_id'] # Safe now

                                    # Get admin username for the notification message
                                    admin_user_for_challenge = database.get_user_by_name(active_challenge['admin_user_id'])
                                    admin_username_for_notification = "the Admin"
                                    if admin_user_for_challenge and admin_user_for_challenge.get('username'):
                                        admin_username_for_notification = admin_user_for_challenge['username']

                                    # Attempt to add participant
                                    join_status = database.add_participant_to_challenge(
                                        challenge_id, self.user_id, MAX_CHALLENGE_PARTICIPANTS # Ensure MAX_CHALLENGE_PARTICIPANTS is defined
                                    )

                                    if join_status == "SUCCESS":
                                        response["status"] = "success"
                                        response["message"] = f"You have successfully joined the challenge (ID: {challenge_id}) in server '{server_name}'."
                                        broadcast_system_message_to_server(
                                            target_server_id,
                                            server_name,
                                            f"{self.username} has joined the challenge against the Admin!",
                                            response,
                                            self.client_socket
                                        )
                                    elif join_status == "ALREADY_JOINED":
                                        response["message"] = "You have already joined this challenge."
                                    elif join_status == "CHALLENGE_FULL":
                                        response["message"] = "This challenge is already full."
                                    elif join_status == "CHALLENGE_NOT_PENDING": # Should be caught earlier, but good fallback
                                        response["message"] = "This challenge is no longer accepting new participants."
                                    elif join_status == "ALREADY_A_PRIMARY_PARTICIPANT": # From add_participant_to_challenge
                                        response["message"] = "You cannot join as an additional participant if you are the admin or original challenger."
                                    else: # CHALLENGE_NOT_FOUND or ERROR from add_participant
                                        response["message"] = f"Could not join challenge (Reason: {join_status})."
                        except ValueError:
                            response["message"] = "Invalid server_id format."
                        except Exception as e_join_chal: # Catch any other unexpected error
                            print(f"DEBUG: [{thread_name}] Exception in JOIN_CHALLENGE for {self.username}: {e_join_chal}")
                            response["message"] = f"An unexpected error occurred while trying to join the challenge: {e_join_chal}"

                    send_json(self.client_socket, response)
                    continue

                elif action == "GET_SERVER_MEMBERS":
                    server_id_to_query_str = payload.get("server_id")
                    response = {"action_response_to": action, "status": "error", "message": "Server ID not provided or invalid."}

                    target_server_id = None
                    if server_id_to_query_str is not None:
                        try:
                            target_server_id = int(server_id_to_query_str)
                        except ValueError:
                            response["message"] = "Invalid server_id format. Must be a number."
                            send_json(self.client_socket, response)
                            continue
                    elif self.current_server_id is not None:
                        target_server_id = self.current_server_id

                    if target_server_id is not None:
                        server_details = database.get_server_details(target_server_id) # Fetches name, admin_user_id, etc.
                        if not server_details:
                            response["message"] = f"Server ID {target_server_id} not found."
                        else:
                            current_server_admin_id = server_details['admin_user_id'] # Get the admin ID for this server
                            db_members = database.get_server_members(target_server_id) # List of {'user_id': X, 'username': 'name'}

                            member_list_with_status = []
                            with lock:
                                for member_data in db_members: # Renamed to avoid conflict if member is a keyword
                                    is_online = member_data['user_id'] in authenticated_clients
                                    is_admin = (member_data['user_id'] == current_server_admin_id) # <<< CHECK IF ADMIN

                                    member_list_with_status.append({
                                        "user_id": member_data['user_id'],
                                        "username": member_data['username'],
                                        "is_online": is_online,
                                        "is_admin": is_admin  # <<< ADD is_admin FLAG TO PAYLOAD
                                    })

                            response["status"] = "success"
                            response["message"] = f"Retrieved members for server '{server_details['name']}'."
                            response["data"] = {
                                "server_id": target_server_id,
                                "server_name": server_details['name'],
                                "members": member_list_with_status # This list now contains the 'is_admin' flag
                            }
                    else:
                        response["message"] = "You must specify a server ID or be active in a server using /server_history."

                    send_json(self.client_socket, response)
                    continue

                # --- Server Management Actions ---
                elif action == "CREATE_SERVER":
                    server_name = payload.get("server_name")
                    if server_name:
                        created_server_info = database.create_server(server_name, self.user_id)
                        if created_server_info: # This is now a dict from create_server
                            response["status"] = "success"
                            response["message"] = f"Server '{server_name}' created successfully."
                            response["data"] = { # Pass the dict directly
                                "server_id": created_server_info['server_id'],
                                "server_name": server_name,
                                "admin_id": self.user_id,
                                "invite_code": created_server_info['invite_code'] # Include invite code
                            }
                        else:
                            response["message"] = f"Failed to create server '{server_name}'. It might already exist or database error."
                    else:
                        response["message"] = "Server name missing in payload for CREATE_SERVER."

                elif action == "CHALLENGE_ADMIN":
                    server_id_str = payload.get("server_id")
                    response = {"action_response_to": action, "status": "error"}

                    if server_id_str is None:
                        response["message"] = "server_id is required."
                    else:
                        try:
                            target_server_id = int(server_id_str)
                            server_details = database.get_server_details(target_server_id)

                            if not server_details:
                                response["message"] = f"Server ID {target_server_id} not found."
                            elif not database.is_user_member(self.user_id, target_server_id):
                                response["message"] = f"You are not a member of server '{server_details['name']}'."
                            elif self.user_id == server_details['admin_user_id']:
                                response["message"] = "You cannot challenge yourself (you are the admin)."
                            elif database.get_active_challenge_for_server(target_server_id):
                                response["message"] = f"An active challenge already exists in server '{server_details['name']}'."
                            else:
                                admin_user_id_to_challenge = server_details['admin_user_id']
                                admin_username_to_challenge = server_details['admin_username'] # From get_server_details

                                challenge_id = database.create_challenge(target_server_id, self.user_id, admin_user_id_to_challenge)
                                if challenge_id:
                                    response["status"] = "success"
                                    response["message"] = (f"Challenge initiated against admin {admin_username_to_challenge} "
                                                           f"in server '{server_details['name']}'. Waiting for admin to accept. Challenge ID: {challenge_id}")
                                    response["data"] = {"challenge_id": challenge_id, "server_name": server_details['name']}

                                    # Broadcast notification to the server
                                    broadcast_challenge_message_to_server(
                                        target_server_id,
                                        server_details['name'],
                                        (f"{self.username} has challenged Admin {admin_username_to_challenge}! "),
                                        response,
                                        self.client_socket
                                    )
                                else:
                                    response["message"] = "Failed to create challenge (database error or active challenge exists)."
                        except ValueError:
                            response["message"] = "Invalid server_id format."
                        except Exception as e_chal:
                            print(f"DEBUG: [{thread_name}] Exception in CHALLENGE_ADMIN: {e_chal}")
                            response["message"] = f"An unexpected error occurred: {e_chal}"

                    send_json(self.client_socket, response)
                    continue

                elif action == "LIST_ALL_SERVERS":
                    all_servers = database.get_all_servers() # This function now returns admin_username too
                    response["status"] = "success"
                    response["message"] = "Retrieved all servers."
                    response["data"] = {"servers": all_servers}

                elif action == "LIST_MY_SERVERS":
                    my_servers = database.get_user_servers(self.user_id) # This now returns invite_code too
                    response["status"] = "success"
                    response["message"] = "Retrieved your servers."
                    response["data"] = {"servers": my_servers} # my_servers now contains invite_code
                    send_json(self.client_socket, response)
                    continue

                elif action == "JOIN_SERVER":
                    invite_code_to_join = payload.get("invite_code")
                    response = {"action_response_to": action, "status": "error"}
                    join_server(self.client_socket, response, self.user_id, self.username, invite_code_to_join)

                elif action == "LEAVE_SERVER":
                    server_id_to_leave_str = payload.get("server_id")
                    # Initialize response with action_response_to for proper client handling
                    response = {"action_response_to": action, "status": "error", "message": "Could not process leave request."}

                    if server_id_to_leave_str is not None:
                        try:
                            server_id_to_leave = int(server_id_to_leave_str)
                            server_details = database.get_server_details(server_id_to_leave)

                            if not server_details:
                                response["message"] = f"Server ID {server_id_to_leave} not found."
                            else:
                                server_name_for_messages = server_details.get('name')

                                if server_name_for_messages is None:
                                    print(f"CRITICAL SERVER ERROR: Server details for ID {server_id_to_leave} fetched but 'name' key is missing or None. Details: {server_details}")
                                    response["message"] = f"Internal error retrieving details for server ID {server_id_to_leave}."
                                else:
                                    leave_result = database.remove_user_from_server(self.user_id, server_id_to_leave)

                                    # Update response based on leave_result
                                    response["status"] = leave_result.get("status", "ERROR") # Default to ERROR if status missing

                                    response_message_for_client = f"Processed leaving server '{server_name_for_messages}'. Status: {response['status']}" # Default
                                    # Customize messages based on specific statuses from remove_user_from_server
                                    if leave_result["status"] == "SUCCESS_LEFT":
                                        response_message_for_client = f"You have left server '{server_name_for_messages}'."
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"{self.username} left the server.", response, self.client_socket)
                                    elif leave_result["status"] == "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED":
                                        new_admin_info = leave_result.get("data", {})
                                        new_admin_username = new_admin_info.get("new_admin_username", "A new user")
                                        response_message_for_client = f"You have left server '{server_name_for_messages}'. {new_admin_username} is the new admin."
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"{self.username} left the server.", response, self.client_socket)
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"New admin is {new_admin_username}.", response, self.client_socket)
                                    elif leave_result["status"] == "SUCCESS_ADMIN_LEFT_SERVER_DELETED":
                                        response_message_for_client = f"You have left server '{server_name_for_messages}'. The server has been deleted."
                                    elif leave_result["status"] == "NOT_MEMBER":
                                        response_message_for_client = f"You are not a member of server '{server_name_for_messages}'."
                                    elif leave_result["status"] == "ERROR_FAILED_TO_ASSIGN_NEW_ADMIN":
                                        response_message_for_client = f"You left as admin from '{server_name_for_messages}', but a new admin could not be assigned."
                                    elif leave_result["status"] == "ERROR":
                                        error_detail_db = leave_result.get("data", {}).get("details", "Database operation failed.")
                                        response_message_for_client = f"Failed to leave server '{server_name_for_messages}'. Detail: {error_detail_db}"

                                    response["message"] = response_message_for_client
                        except ValueError:
                            response["message"] = "Invalid server_id format for LEAVE_SERVER."
                        except Exception as e_leave: # Catch any other unexpected error in this block
                            print(f"DEBUG: [{thread_name}] Unexpected Exception in LEAVE_SERVER for {self.username}: {e_leave}")
                            response["message"] = f"An unexpected error occurred while trying to leave the server: {e_leave}"
                            # Ensure status is error if not already set by a more specific condition
                            response["status"] = "error"

                    else: # server_id_to_leave_str was None
                        response["message"] = "server_id missing in payload for LEAVE_SERVER."

                    send_json(self.client_socket, response)
                    continue

                elif action == "SERVER_HISTORY":
                    server_id_str = payload.get("server_id")
                    if server_id_str is None:
                        response["message"] = "server_id is required for SERVER_HISTORY."
                    else:
                        try:
                            target_server_id = int(server_id_str)
                            if database.is_user_member(self.user_id, target_server_id): # Check membership
                                server_details = database.get_server_details(target_server_id)
                                server_name = server_details.get('name', 'Unknown Server') if server_details else 'Unknown Server'
                                recent_messages = database.get_messages_for_server(target_server_id, limit=50)

                                response["status"] = "success"
                                response["message"] = f"Message history for server '{server_name}'."
                                response["data"] = {
                                    "server_id": target_server_id,
                                    "server_name": server_name,
                                    "messages": recent_messages
                                }
                                self.current_server_id = target_server_id # <<< SET Current Server ID
                            else:
                                response["message"] = f"You are not a member of server ID {target_server_id} or it does not exist."
                        except ValueError:
                            response["message"] = "Invalid server_id format for SERVER_HISTORY."
                    send_json(self.client_socket, response)
                    continue

                else: # Default case for unknown actions during an authenticated session
                    response["message"] = f"Unknown or unsupported action: {action}"

                # Send the determined response back to the client for most actions
                if action not in ["SEND_CHAT_MESSAGE", "DISCONNECT", "JOIN_SERVER", "LEAVE_SERVER", "ACCEPT_CHALLENGE", "JOIN_CHALLENGE", "CHALLENGE_ADMIN", "KICK_USER", "SERVER_HISTORY", "GET_SERVER_MEMBERS"]: # <<< Update list
                    send_json(self.client_socket, response)

        except Exception as e:
            print(f"DEBUG: [{thread_name}] General Exception in ClientThread.run for {self.username}: {e}")
            self.running = False
        finally:
            print(f"DEBUG: [{thread_name}] **Executing finally block in ClientThread for User {self.username}**")
            with lock:
                if self.user_id in authenticated_clients:
                    del authenticated_clients[self.user_id]
                leave_broadcast = {
                    "type": "USER_LEFT",
                    "payload": {"username": self.username, "user_id": self.user_id, "timestamp": int(time.time())}
                }
                # Kill any game process started by this user (if any logic depends on it)
                # This part is tricky - usually only admins start games. Let's skip auto-kill for now.

                for target_user_id_final, client_info_final in authenticated_clients.items(): # Corrected variable names
                    send_json(client_info_final['socket'], leave_broadcast)
            try:
                self.client_socket.close()
            except Exception as e_close:
                 print(f"DEBUG: [{thread_name}] Exception during socket close for {self.username}: {e_close}")
            print(f"DEBUG: [{thread_name}] ClientThread for {self.username} finished.")



def handle_client(client_socket, addr):
    thread_name = threading.current_thread().name
    print(f"DEBUG: [{thread_name}] handle_client started for {addr}")
    socket_handed_off = False

    try:
        while not socket_handed_off: # Loop only for authentication phase
            print(f"DEBUG: [{thread_name}] handle_client for {addr} waiting for auth JSON...")
            request_data = receive_json(client_socket)

            if request_data is None: # Connection closed or error
                print(f"DEBUG: [{thread_name}] Client {addr} disconnected or bad data during auth.")
                break # Exit auth loop, connection will be closed in finally

            if mongodb_logging_active: # Check before calling log function
                # For unauthenticated phase, user_details might be None or just basic
                log_to_mongodb("RECEIVED_FROM_CLIENT", addr, None, request_data)

            print(f"DEBUG: [{thread_name}] Received from {addr} for auth: {request_data}")

            action = request_data.get("action")
            payload = request_data.get("payload", {})
            response = {"action_response_to": action} # Base for response

            if action == "REGISTER":
                username = payload.get("username")
                password = payload.get("password")
                if not username or not password:
                    response["status"] = "error"
                    response["message"] = "Username and password required for registration."
                elif database.add_user(username, password):
                    response["status"] = "success"
                    response["message"] = "Registration successful. Please login."
                else:
                    response["status"] = "error"
                    response["message"] = "Registration failed. Username may be taken or server error."
                send_json(client_socket, response)

            elif action == "LOGIN":
                username = payload.get("username")
                password = payload.get("password")
                if not username or not password:
                    response["status"] = "error"
                    response["message"] = "Username and password required for login."
                    send_json(client_socket, response)
                    continue # Allow retry

                auth_user_id = database.check_user_credentials(username, password)
                if auth_user_id:
                    with lock: # Check if already logged in
                        if auth_user_id in authenticated_clients:
                            response["status"] = "error"
                            response["message"] = "User already logged in elsewhere."
                            send_json(client_socket, response)
                            continue # Allow retry with different credentials or client can decide to quit

                    response["status"] = "success"
                    response["message"] = f"Welcome {username}!"
                    response["data"] = {"user_id": auth_user_id, "username": username}
                    send_json(client_socket, response)

                    print(f"DEBUG: [{thread_name}] Starting ClientThread for {addr} (User: {username}, ID: {auth_user_id})")
                    t = ClientThread(client_socket, addr, auth_user_id, username)
                    t.start()
                    socket_handed_off = True # Set flag
                    print(f"DEBUG: [{thread_name}] ClientThread started. Socket handoff flag set. **Returning from handle_client.**")
                    return # Exit handle_client
                else:
                    response["status"] = "error"
                    response["message"] = "Invalid username or password."
                    send_json(client_socket, response)

            else: # Unknown action during auth phase
                response["status"] = "error"
                response["message"] = f"Invalid action during auth: {action}. Expecting REGISTER or LOGIN."
                send_json(client_socket, response)

            # If loop continues, it means auth wasn't successful and handed off yet.

    except Exception as e: # Catch-all for unexpected errors in auth loop
        print(f"DEBUG: [{thread_name}] Exception in handle_client for {addr}: {e}")
    finally:
        print(f"DEBUG: [{thread_name}] **Executing finally block in handle_client for {addr}.**")
        if not socket_handed_off:
            print(f"DEBUG: [{thread_name}] Socket NOT handed off. Closing connection for {addr} from handle_client.")
            try:
                client_socket.close()
            except: pass # Ignore errors on close if already closed
        else:
            print(f"DEBUG: [{thread_name}] Socket WAS handed off. Not closing from handle_client.")
        print(f"DEBUG: [{thread_name}] handle_client for {addr} finished execution path.")

# ... (init_server and __main__ remain largely the same, ensure init_server calls the modified handle_client) ...
# Ensure 'socket' and 'threading' are imported at the top of server.py if they were missing


def init_server(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow address reuse immediately
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Socket successfully created")
        s.bind(('0.0.0.0', port))
        print(f"Socket binded to {port}")
        s.listen(5) # Max 5 queued connections
        print("Socket is listening...")
        while True:
            client_socket, addr = s.accept()
            print(f"Accepted new connection from {addr[0]}:{addr[1]}")
            # Create a new thread to handle the client's authentication and subsequent communication
            auth_thread = threading.Thread(target=handle_client, args=(client_socket, addr,))
            auth_thread.daemon = True # Optional: allow main program to exit even if auth_threads are running
            auth_thread.start()
    except Exception as error:
        print(f"Server error in init_server: {error}")
    finally:
        if 's' in locals() and s: # Check if s was defined and is not None
            s.close()
            print("Server socket closed.")
        # <<< ADDED: Cleanup running game processes on server exit >>>
        with lock:
            print("SERVER: Cleaning up running game processes...")
            for challenge_id, proc in list(game_processes.items()):
                 print(f"SERVER: Terminating game process for challenge {challenge_id} (PID: {proc.pid})")
                 try:
                     proc.terminate()
                     proc.wait(timeout=2)
                 except subprocess.TimeoutExpired:
                     proc.kill()
                 except Exception as e_kill:
                     print(f"SERVER: Error terminating game process {proc.pid}: {e_kill}")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server.py <port>")
        sys.exit(1)

    try:
        port_num = int(sys.argv[1])
        if not (1024 <= port_num <= 65535):
            raise ValueError("Port number must be between 1024 and 65535.")
    except ValueError as e:
        print(f"Invalid port number: {e}")
        sys.exit(1)

    # Clear console
    os.system('cls' if os.name == 'nt' else 'clear')

    print("Initializing database...")
    database.initialize_database()

    print(f"Starting server on port {port_num}...")
    init_server(port_num)