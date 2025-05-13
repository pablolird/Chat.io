# Refine Server-Specific Messaging
import socket          
import threading
import os
import sys
import database # Your database module
import json
import time

# BUFFER_SIZE = 1024 # Already implicitly used by recv(1024)

def send_json(sock, data_dict):
    """Safely send a dictionary as a JSON string."""
    try:
        message = json.dumps(data_dict)
        sock.sendall(message.encode('utf-8')) # sendall tries to send all data
        return True
    except Exception as e:
        # Log the error and the socket for which it occurred
        # print(f"Error sending JSON data to {sock.getpeername() if sock else 'N/A'}: {e}")
        # print(f"Data that failed to send: {data_dict}")
        return False

def receive_json(sock):
    """Receive data and attempt to parse it as JSON.
       Handles potential incomplete messages or multiple messages by simple buffering.
       NOTE: This is a simplified version. For very robust handling of arbitrary length
       JSON or multiple messages in one recv, a more complex framing protocol
       (e.g., length prefix or newline delimiters for multiple JSONs) would be needed.
       For now, we assume one JSON per primary send/recv interaction or that
       JSON objects are not excessively large to be fragmented often within 1024 bytes.
    """
    try:
        data_bytes = sock.recv(1024) # Using the existing buffer size
        if not data_bytes:
            return None # Connection closed
        
        # Basic attempt to handle potentially multiple JSON objects if they are small and arrive together
        # This is still not perfectly robust for all scenarios but better than a raw decode.
        # A better way is proper message framing (length prefix or delimiters).
        decoded_data = data_bytes.decode('utf-8')
        
        # Try to parse directly. If it fails, it might be an incomplete JSON or other error.
        try:
            return json.loads(decoded_data)
        except json.JSONDecodeError as je:
            # This could be due to incomplete JSON or other data.
            # For now, we'll log and return None, indicating a parsing failure.
            # In a more robust system, you'd buffer and wait for more data if incomplete.
            # print(f"JSONDecodeError for {sock.getpeername() if sock else 'N/A'}: {je} - Data: '{decoded_data}'")
            # Raise a custom error or return a specific marker if needed by caller
            return {"status": "error", "message": "Received malformed JSON or incomplete data."}


    except ConnectionResetError:
        # print(f"Connection reset by peer {sock.getpeername() if sock else 'N/A'} during receive_json.")
        return None # Indicate connection closed
    except Exception as e:
        # print(f"Error receiving/decoding JSON data from {sock.getpeername() if sock else 'N/A'}: {e}")
        return None


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
        self.current_server_id = None # User is not in any server initially

        thread_name = threading.current_thread().name
        print(f"DEBUG: [{thread_name}] ClientThread __init__ for UserID: {self.user_id}, Username: {self.username}, Addr: {self.addr}")
        with lock:
            authenticated_clients[self.user_id] = {
                'socket': self.client_socket,
                'username': self.username,
                'addr': self.addr,
                'current_server_id': self.current_server_id # Initialized to None here
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
                    message_content = payload.get("message")
                    response = {"action_response_to": action, "status": "error"} # For sending error back to sender

                    if not self.current_server_id:
                        response["message"] = "You must enter a server first to send messages. Use /enter_server <id>."
                        send_json(self.client_socket, response)
                        continue # Skip further processing for this action

                    if message_content:
                        # 1. Persist the message
                        message_id = database.add_message(self.current_server_id, self.user_id, message_content)

                        if message_id:
                            # 2. Construct the broadcast message
                            chat_message_broadcast = {
                                "type": "NEW_CHAT_MESSAGE",
                                "payload": {
                                    "sender_username": self.username,
                                    "sender_user_id": self.user_id,
                                    "message": message_content,
                                    "timestamp": int(time.time()),
                                    "server_id": self.current_server_id, # Include server_id in broadcast
                                    "message_id": message_id # Optionally include message_id
                                }
                            }
                            print(f"DEBUG: [{thread_name}] Broadcasting to server {self.current_server_id} from {self.username}: {message_content}")
                            
                            # 3. Targeted Broadcasting
                            with lock:
                                for target_user_id, client_info in authenticated_clients.items():
                                    # Send only to users in the same current_server_id
                                    if client_info['current_server_id'] == self.current_server_id:
                                        # Optionally, don't send back to the original sender if client handles local echo
                                        # if target_user_id != self.user_id: 
                                        send_json(client_info['socket'], chat_message_broadcast)
                            # No direct "success" response to the sender for a chat message usually,
                            # they see their own message via local echo or the broadcast.
                            continue # Skip sending default response
                        else:
                            response["message"] = "Failed to save your message to the database."
                            send_json(self.client_socket, response)
                            continue
                    else:
                        response["message"] = "Message content missing."
                        send_json(self.client_socket, response)
                        continue
                
                elif action == "DISCONNECT":
                    print(f"DEBUG: [{thread_name}] User {self.username} sent DISCONNECT.")
                    self.running = False
                    # No response needed, client will close. Server closes in finally.
                    break 

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
                                # TODO: Optionally broadcast USER_JOINED_SERVER to members of that server
                            else:
                                response["message"] = f"Failed to join server ID {server_id_to_join}."
                        except ValueError:
                            response["message"] = "Invalid server_id format for JOIN_SERVER."
                    else:
                        response["message"] = "server_id missing in payload for JOIN_SERVER."
                
                elif action == "LEAVE_SERVER":
                    server_id_to_leave = payload.get("server_id")
                    if server_id_to_leave is not None:
                        try:
                            server_id_to_leave = int(server_id_to_leave)
                            server_details = database.get_server_details(server_id_to_leave) # Get name for messages
                            if not server_details:
                                response["message"] = f"Server ID {server_id_to_leave} not found."
                            else:
                                leave_status = database.remove_user_from_server(self.user_id, server_id_to_leave)
                                response["status"] = "success" # Assume success unless specific error from DB
                                if leave_status == "SUCCESS_LEFT":
                                    response["message"] = f"You have left server '{server_details['name']}'."
                                elif leave_status == "SUCCESS_ADMIN_LEFT_NEW_ADMIN_ASSIGNED":
                                    response["message"] = f"You have left server '{server_details['name']}'. A new admin has been assigned."
                                    # TODO: Broadcast new admin to remaining server members
                                elif leave_status == "SUCCESS_ADMIN_LEFT_SERVER_DELETED":
                                    response["message"] = f"You have left server '{server_details['name']}'. The server has been deleted."
                                elif leave_status == "NOT_MEMBER":
                                    response["status"] = "error"
                                    response["message"] = f"You are not a member of server '{server_details['name']}'."
                                elif leave_status == "SERVER_NOT_FOUND": # Should have been caught above
                                    response["status"] = "error"
                                    response["message"] = f"Server ID {server_id_to_leave} not found."
                                else: # "ERROR" or "ERROR_FAILED_TO_ASSIGN_NEW_ADMIN"
                                    response["status"] = "error"
                                    response["message"] = f"Could not process leaving server '{server_details['name']}'. Status: {leave_status}"
                        except ValueError:
                            response["message"] = "Invalid server_id format for LEAVE_SERVER."
                    else:
                        response["message"] = "server_id missing in payload for LEAVE_SERVER."

                elif action == "ENTER_SERVER":
                    server_id_to_enter = payload.get("server_id")
                    response = {"action_response_to": action, "status": "error"} # Default error
                    if server_id_to_enter is not None:
                        try:
                            server_id_to_enter = int(server_id_to_enter)
                            if database.is_user_member(self.user_id, server_id_to_enter):
                                self.current_server_id = server_id_to_enter
                                # Update the global state for this user
                                with lock:
                                    if self.user_id in authenticated_clients:
                                        authenticated_clients[self.user_id]['current_server_id'] = self.current_server_id
                                
                                server_details = database.get_server_details(server_id_to_enter)
                                server_name = server_details.get('name', 'Unknown Server') if server_details else 'Unknown Server'
                                
                                # Fetch recent messages for this server
                                recent_messages = database.get_messages_for_server(self.current_server_id, limit=50) # Assuming get_messages... returns list of dicts

                                response["status"] = "success"
                                response["message"] = f"Entered server '{server_name}' (ID: {self.current_server_id})."
                                response["data"] = {
                                    "current_server_id": self.current_server_id,
                                    "server_name": server_name,
                                    "messages": recent_messages # Send message history
                                }
                                print(f"DEBUG: [{thread_name}] User {self.username} entered server {server_name} (ID: {self.current_server_id})")
                            else:
                                response["message"] = f"You are not a member of server ID {server_id_to_enter}, or server does not exist."
                        except ValueError:
                             response["message"] = "Invalid server_id format for ENTER_SERVER."
                    else:
                        response["message"] = "server_id missing for ENTER_SERVER."
                    send_json(self.client_socket, response)
                    continue # Processed this action

                else: # Default case for unknown actions during an authenticated session
                    response["message"] = f"Unknown or unsupported action: {action}"
                
                # Send the determined response back to the client for most actions
                if action not in ["SEND_CHAT_MESSAGE", "DISCONNECT"]: # These don't get a direct "response" in this flow
                    send_json(self.client_socket, response)

        except Exception as e:
            print(f"DEBUG: [{thread_name}] General Exception in ClientThread.run for {self.username}: {e}")
            self.running = False
        finally:
            # ... (Your existing finally block for ClientThread to remove user, broadcast leave, close socket) ...
            # (Ensure it uses authenticated_clients and self.user_id correctly)
            print(f"DEBUG: [{thread_name}] **Executing finally block in ClientThread for User {self.username}**")
            with lock:
                if self.user_id in authenticated_clients:
                    del authenticated_clients[self.user_id]
                
                leave_broadcast = {
                    "type": "USER_LEFT", # Global "left the system" message
                    "payload": {"username": self.username, "user_id": self.user_id, "timestamp": int(time.time())}
                }
                for target_user_id, client_info in authenticated_clients.items():
                    send_json(client_info['socket'], leave_broadcast)
            
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