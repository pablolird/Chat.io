# Refine Server-Specific Messaging
import socket          
import threading
import os
import sys
import database # Your database module
import json
import time
import struct

MSG_LENGTH_PREFIX_FORMAT = '!I'  # Network byte order, Unsigned Integer (4 bytes)
MSG_LENGTH_PREFIX_SIZE = struct.calcsize(MSG_LENGTH_PREFIX_FORMAT)
SUPERUSER_ID = 1
SUPERUSER_USERNAME = "SYSTEM"

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

def send_json(sock, data_dict):
    try:
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

def broadcast_system_message_to_server(server_id, server_name, message_text):
    thread_name = threading.current_thread().name # Get current thread name for logging
    print(f"DEBUG: [{thread_name}] Attempting to broadcast SYSTEM message to server_id {server_id} ('{server_name}'): {message_text}")

    system_message_payload = {
        "type": "CHAT_MESSAGE", # Use the existing chat message type
        "payload": {
            "sender_user_id": SUPERUSER_ID,
            "sender_username": SUPERUSER_USERNAME,
            "message": message_text,
            "timestamp": int(time.time()),
            "server_id": server_id,
            "server_name": server_name 
        }
    }

    members_of_server = database.get_server_members(server_id) 
    if not members_of_server:
        print(f"DEBUG: [{thread_name}] No members found for server_id {server_id} to broadcast system message.")
        return

    with lock: 
        online_recipients = 0
        for member in members_of_server:
            member_id = member['user_id']
            if member_id in authenticated_clients:
                client_info = authenticated_clients[member_id]
                if send_json(client_info['socket'], system_message_payload):
                    online_recipients += 1
        print(f"DEBUG: [{thread_name}] System message broadcast to {online_recipients}/{len(members_of_server)} members of server_id {server_id}.")

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
                        if not server_details:
                            response["message"] = f"Server ID {target_server_id} not found."
                            send_json(self.client_socket, response)
                            continue
                        
                        if not database.is_user_member(self.user_id, target_server_id):
                            response["message"] = f"You are not a member of server '{server_details['name']}'."
                            send_json(self.client_socket, response)
                            continue

                        # Persist the message
                        message_id = database.add_message(target_server_id, self.user_id, message_content)
                        if message_id:
                            chat_message_broadcast = {
                                "type": "CHAT_MESSAGE",
                                "payload": {
                                    "sender_username": self.username,
                                    "sender_user_id": self.user_id,
                                    "message": message_content,
                                    "timestamp": int(time.time()),
                                    "server_id": target_server_id,
                                    "server_name": server_details['name'], # Include server name
                                    "message_id": message_id
                                }
                            }
                            print(f"DEBUG: [{thread_name}] Relaying message from {self.username} to server '{server_details['name']}' (ID: {target_server_id})")
                            
                            # Broadcast to all online members of that specific server
                            server_members = database.get_server_members(target_server_id)
                            with lock:
                                for member in server_members:
                                    member_id = member['user_id']
                                    if member_id in authenticated_clients: # Check if member is online
                                        # No need to check if member_id != self.user_id if client handles its own messages
                                        send_json(authenticated_clients[member_id]['socket'], chat_message_broadcast)
                            # No direct response to sender for SEND_CHAT_MESSAGE usually
                            continue 
                        else:
                            response["message"] = "Failed to save your message."
                            send_json(self.client_socket, response)
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
                        new_server_id = database.create_server(server_name, self.user_id)
                        if new_server_id:
                            response["status"] = "success"
                            response["message"] = f"Server '{server_name}' created successfully."
                            response["data"] = {"server_id": new_server_id, "server_name": server_name, "admin_id": self.user_id}
                        else:
                            response["message"] = f"Failed to create server '{server_name}'. It might already exist or database error."
                    else:
                        response["message"] = "Server name missing in payload for CREATE_SERVER."
                
                elif action == "LIST_ALL_SERVERS":
                    all_servers = database.get_all_servers() # This function now returns admin_username too
                    response["status"] = "success"
                    response["message"] = "Retrieved all servers."
                    response["data"] = {"servers": all_servers}

                elif action == "LIST_MY_SERVERS":
                    my_servers = database.get_user_servers(self.user_id) # This function now returns admin_username too
                    response["status"] = "success"
                    response["message"] = "Retrieved your servers."
                    response["data"] = {"servers": my_servers}

                elif action == "JOIN_SERVER":
                    server_id_to_join = payload.get("server_id")
                    if server_id_to_join is not None:
                        try:
                            server_id_to_join = int(server_id_to_join)
                            # Check if server exists
                            server_details = database.get_server_details(server_id_to_join)
                            if not server_details:
                                response["message"] = f"Server ID {server_id_to_join} not found."
                            elif database.is_user_member(self.user_id, server_id_to_join):
                                response["status"] = "error" # Or "info"
                                response["message"] = f"You are already a member of server '{server_details['name']}'."
                            elif database.add_user_to_server(self.user_id, server_id_to_join):
                                response["status"] = "success"
                                response["message"] = f"Successfully joined server '{server_details['name']}'."
                                send_json(self.client_socket, response) # Send response to joining user first
                                # Now broadcast to the server
                                broadcast_system_message_to_server(server_id_to_join, server_details['name'], f"{self.username} joined the server.")
                            else:
                                response["message"] = f"Failed to join server ID {server_id_to_join}."
                        except ValueError:
                            response["message"] = "Invalid server_id format for JOIN_SERVER."
                    else:
                        response["message"] = "server_id missing in payload for JOIN_SERVER."
                
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
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"{self.username} left the server.")
                                    elif leave_result["status"] == "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED":
                                        new_admin_info = leave_result.get("data", {})
                                        new_admin_username = new_admin_info.get("new_admin_username", "A new user")
                                        response_message_for_client = f"You have left server '{server_name_for_messages}'. {new_admin_username} is the new admin."
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"{self.username} left the server.")
                                        broadcast_system_message_to_server(server_id_to_leave, server_name_for_messages, f"New admin is {new_admin_username}.")
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
                            else:
                                response["message"] = f"You are not a member of server ID {target_server_id} or it does not exist."
                        except ValueError:
                            response["message"] = "Invalid server_id format for SERVER_HISTORY."
                    send_json(self.client_socket, response)
                    continue

                else: # Default case for unknown actions during an authenticated session
                    response["message"] = f"Unknown or unsupported action: {action}"
                
                # Send the determined response back to the client for most actions
                if action not in ["SEND_CHAT_MESSAGE", "DISCONNECT"]: # These don't get a direct "response" in this flow
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