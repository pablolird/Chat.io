# CLIENT.PY
import socket
import os
import threading
import sys
import json
import getpass
import time
import struct
import subprocess # <<< ADDED

MSG_LENGTH_PREFIX_FORMAT = '!I'  # Network byte order, Unsigned Integer (4 bytes)
MSG_LENGTH_PREFIX_SIZE = struct.calcsize(MSG_LENGTH_PREFIX_FORMAT)
GODOT_EXECUTABLE_PATH = "/home/cxn/Documents/code/python/Database Systems/chat app/Chat-App---Final-Project/GodotGame/FinalLinux.x86_64" # <<< ADDED: Path to your game executable

def send_json_client(sock, data_dict):
    try:
        json_bytes = json.dumps(data_dict).encode('utf-8')
        len_prefix = struct.pack(MSG_LENGTH_PREFIX_FORMAT, len(json_bytes))
        sock.sendall(len_prefix)
        sock.sendall(json_bytes)
        return True
    except BrokenPipeError:
        print("CLIENT: Broken pipe. Server connection lost.")
        global running
        running = False
        return False
    except Exception as e:
        print(f"CLIENT: Error sending JSON: {e}")
        return False

def receive_all(sock, num_bytes_to_receive):
    received_data = bytearray()
    while len(received_data) < num_bytes_to_receive:
        try:
            bytes_to_get_now = min(num_bytes_to_receive - len(received_data), 4096)
            packet = sock.recv(bytes_to_get_now)
        except socket.timeout:
            print("CLIENT: Socket timeout during receive_all.")
            return None # Indicate timeout
        except ConnectionAbortedError:
            print("CLIENT: Connection aborted during receive_all.")
            return None
        except Exception as e: # Other socket errors
            print(f"CLIENT: Socket error during receive_all: {e}")
            return None

        if not packet:
            # Connection closed prematurely by the server
            print("CLIENT: Connection closed by server while expecting more data in receive_all.")
            return None
        received_data.extend(packet)
    return received_data

def receive_json_client(sock):
    global running
    try:
        # 1. Receive the 4-byte length prefix
        len_prefix_bytes = receive_all(sock, MSG_LENGTH_PREFIX_SIZE)
        if len_prefix_bytes is None:
            if running: running = False
            return None

        # 2. Unpack the length prefix to get the message length
        actual_message_length = struct.unpack(MSG_LENGTH_PREFIX_FORMAT, len_prefix_bytes)[0]
        print(f"CLIENT DEBUG: Expecting JSON message of length: {actual_message_length}")

        # 3. Receive the actual JSON message data
        json_message_bytes = receive_all(sock, actual_message_length)
        if json_message_bytes is None:
            if running: running = False
            return None

        # 4. Decode from UTF-8 and parse JSON
        json_string = json_message_bytes.decode('utf-8')
        print(f"CLIENT DEBUG: Received JSON string: {json_string[:200]}...")
        return json.loads(json_string)

    except struct.error as se:
        print(f"CLIENT: Struct unpack error (likely bad length prefix from server or connection issue): {se}")
        if running: running = False
        return None
    except json.JSONDecodeError as je:
        print(f"CLIENT: Failed to decode JSON received from server. Error: {je}")
        print(f"CLIENT DEBUG MALFORMED JSON DATA: <{json_message_bytes.decode('utf-8', errors='ignore') if 'json_message_bytes' in locals() else 'Could not decode for debug'}>")
        if running: running = False
        return {"status": "error", "message": "Malformed JSON received from server (decode error)."} # Or None
    except Exception as e:
        print(f"CLIENT: Critical error in receive_json_client: {e}")
        if running: running = False
        return None

running = True
authenticated_user_details = None # Stores {'user_id': id, 'username': name}
current_server_context_name = "Global" # Default context name for the prompt
client_active_server_id = None

def format_timestamp(unix_ts):
    """Helper to format Unix timestamp into a readable string."""
    if unix_ts is None:
        return ""
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(unix_ts)))
    except:
        return str(unix_ts) # Fallback

def get_prompt():
    if authenticated_user_details:
        return f"{authenticated_user_details['username']}> " # Simplified prompt
    return "> "

def sendingThread(sock):
    global running
    global authenticated_user_details
    # global current_server_context_name # Used by get_prompt()
    global client_active_server_id # Used to provide default server_id

    print(f"\n--- Type /help for commands, or your message to chat. ---")
    sys.stdout.write(get_prompt())
    sys.stdout.flush()

    while running:
        try:
            user_input = input()
            if not running: break

            request_json = None
            command_processed = False

            if user_input.startswith("/"):
                command_processed = True
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()

                args_str = parts[1] if len(parts) > 1 else ""
                args_list = args_str.split() # Further split args if needed by specific commands

                if command == "/close":
                    request_json = {"action": "DISCONNECT"}

                elif command == "/create_server":
                    if len(args_str):
                        request_json = {"action": "CREATE_SERVER", "payload": {"server_name": args_str}}
                    else:
                        print("CLIENT: Usage: /create_server <server_name>")

                elif command == "/list_servers":
                    request_json = {"action": "LIST_ALL_SERVERS"}

                elif command == "/my_servers":
                    request_json = {"action": "LIST_MY_SERVERS"}

                elif command == "/users_in_server": # <<< NEW COMMAND
                    target_server_id_for_request = None
                    if len(args_list) == 1: # User provided a server ID
                        try:
                            target_server_id_for_request = int(args_list[0])
                        except ValueError: print("CLIENT: Invalid server ID. Must be a number.")
                    else: print("CLIENT: Usage: /users_in_server <server_id>")
                    if target_server_id_for_request is not None:
                        request_json = {"action": "GET_SERVER_MEMBERS", "payload": {"server_id": target_server_id_for_request}}

                elif command == "/join_server": # Renamed from /join_server
                    if args_str: # Expecting a single argument: the invite code
                        invite_code = args_str
                        request_json = {"action": "JOIN_SERVER", "payload": {"invite_code": invite_code}}
                    else:
                        print("CLIENT: Usage: /join_server <invite_code>")

                elif command == "/leave_server":
                    if len(args_list) == 1:
                        try:
                            server_id = int(args_list[0])
                            request_json = {"action": "LEAVE_SERVER", "payload": {"server_id": server_id}}
                        except ValueError: print("CLIENT: Invalid server ID. Must be a number.")
                    else: print("CLIENT: Usage: /leave_server <server_id>")

                elif command == "/server_history":
                    if len(args_list) == 1:
                        try:
                            server_id = int(args_list[0])
                            request_json = {"action": "SERVER_HISTORY", "payload": {"server_id": server_id}}
                        except ValueError: print("CLIENT: Invalid server ID. Must be a number.")
                    else: print("CLIENT: Usage: /server_history <server_id>")

                elif command == "/accept_challenge":
                    if len(args_list) == 1:
                        try:
                            server_id = int(args_list[0])
                            request_json = {"action": "ACCEPT_CHALLENGE", "payload": {"server_id": server_id}} # Action "ACCEPT_CHALLENGE"
                        except ValueError:
                            print("CLIENT: Invalid server ID for /accept_challenge.")
                    else:
                        print("CLIENT: Usage: /accept_challenge <server_id> (to accept challenge in that server)")

                elif command == "/join_challenge":
                    if len(args_list) == 1:
                        try:
                            server_id = int(args_list[0])
                            request_json = {"action": "JOIN_CHALLENGE", "payload": {"server_id": server_id}}
                        except ValueError:
                            print("CLIENT: Invalid server ID for /join_challenge.")
                    else:
                        print("CLIENT: Usage: /join_challenge <server_id> (to join the active challenge in that server)")

                elif command == "/challenge_server_admin":
                    if len(args_list) == 1:
                        try:
                            server_id = int(args_list[0])
                            request_json = {"action": "CHALLENGE_ADMIN", "payload": {"server_id": server_id}}
                        except ValueError:
                            print("CLIENT: Invalid server ID for /challenge_server_admin.")
                    else:
                        print("CLIENT: Usage: /challenge_server_admin <server_id>")

                elif command == "/user_kick":
                    if len(args_list) == 2: # Expects <server_id> <user_to_kick_id>
                        try:
                            server_id_to_act_on = int(args_list[0])
                            user_id_to_kick_val = int(args_list[1])
                            request_json = {
                                "action": "KICK_USER",
                                "payload": {
                                    "server_id": server_id_to_act_on,
                                    "user_to_kick_id": user_id_to_kick_val
                                }
                            }
                        except ValueError:
                            print("CLIENT: Invalid server_id or user_id. Both must be numbers.")
                    else:
                        print("CLIENT: Usage: /user_kick <server_id> <user_id_to_kick>")

                elif command == "/message":
                    msg_parts = args_str.split(maxsplit=1)
                    if len(msg_parts) == 2:
                        try:
                            server_id = int(msg_parts[0])
                            message_content = msg_parts[1]
                            if message_content:
                                request_json = {"action": "SEND_CHAT_MESSAGE", "payload": {"server_id": server_id, "message": message_content}}
                            else: print("CLIENT: Message content cannot be empty for /message.")
                        except ValueError: print("CLIENT: Invalid server_id for /message.")
                    else: print("CLIENT: Usage: /message <server_id> <message_content>")

                elif command == "/help":
                    print("\nCLIENT: Available commands:")
                    print("  /create_server <name>   - Create a new server.")
                    print("  /list_servers           - List all available servers.")
                    print("  /my_servers             - List servers you are a member of.")
                    print("  /join_server <code>     - Join a server by its ID.")
                    print("  /server_history <id>    - Set a server as your active context.")
                    print("  /leave_server <id>      - Leave a server by its ID.")
                    print("  /users_in_server [id]   - List users in a server (current if no id).")
                    print("  /message <id> <message> - Message to that specific server.")
                    print("  /close                  - Disconnect from the chat.")
                    print("  /help                   - Show this help message.")
                    print("  /user_kick <server_id> <user_id> - ")
                    print("  /challenge_server_admin <server_id> - ")
                    print("  /join_challenge <server_id>")
                    print("  /accept_challenge <server_id> ")
                else:
                    print(f"CLIENT: Unknown command: {command}. Type /help for commands.")

                if not request_json and command_processed:
                    sys.stdout.write(get_prompt())
                    sys.stdout.flush()
            else:
                print("CLIENT: Invalid input. Type /help for commands or /message <server_id> <message> to chat.")
                sys.stdout.write(get_prompt()); sys.stdout.flush()

            if request_json:
                if not send_json_client(sock, request_json):
                    print("CLIENT: Failed to send request to server. Disconnecting.")
                    running = False
                if request_json.get("action") == "DISCONNECT":
                    running = False
                    break
        except EOFError:
            print("\nCLIENT: EOF detected. Sending disconnect.")
            running = False
            send_json_client(sock, {"action": "DISCONNECT"})
            break
        except KeyboardInterrupt:
            print("\nCLIENT: KeyboardInterrupt. Sending disconnect.")
            running = False
            send_json_client(sock, {"action": "DISCONNECT"})
            break
        except Exception as e:
            if running:
                print(f"CLIENT: Error in sending thread: {e}")
            running = False
            break
    print("CLIENT: Sending thread stopped.")


def receivingThread(sock):
    global running
    global authenticated_user_details
    global current_server_context_name
    global client_active_server_id

    while running:
        try:
            response_data = receive_json_client(sock)
            if response_data is None:
                if running:
                    print("\rCLIENT: Disconnected from server (receiver).")
                running = False
                break

            prompt_len = len(get_prompt())
            sys.stdout.write('\r' + ' ' * (prompt_len + 100) + '\r')

            action_response = response_data.get("action_response_to")
            status = response_data.get("status")
            message = response_data.get("message", "")
            data = response_data.get("data", {})

            if action_response:
                print(f"SERVER ({action_response} - {status}): {message}")
                if status == "success":
                    if action_response == "LIST_ALL_SERVERS" or action_response == "LIST_MY_SERVERS":
                        servers = data.get("servers", [])
                        if servers:
                            print("  Servers:")
                            for server_item in servers:
                                admin_info = f"Admin: {server_item.get('admin_username', 'N/A')}"
                                invite_info = ""
                                if action_response == "LIST_MY_SERVERS": # Only show invite code for /my_servers
                                    invite_info = f", Invite Code: {server_item.get('invite_code', 'N/A')}"
                                print(f"    ID: {server_item.get('server_id')}, Name: \"{server_item.get('name')}\", {admin_info}{invite_info}")
                        else:
                            print("  No servers to display.")

                    elif action_response == "CREATE_SERVER":
                        if status == "success":
                            print(f"  Server Name: '{data.get('server_name')}', ID: {data.get('server_id')}")
                            print(f"  Invite Code: {data.get('invite_code')}") # Display invite code

                    elif action_response == "SERVER_HISTORY": # Ensure this part is correct from previous step
                        server_name = data.get("server_name", "UnknownServer")
                        messages_history = data.get("messages", [])
                        print(f"  --- Message History for '{server_name}' (ID: {data.get('server_id')}) ---")
                        if messages_history:
                            for msg_data in messages_history:
                                ts = format_timestamp(msg_data.get('timestamp'))
                                sender = msg_data.get('sender_username', 'Unknown')
                                content = msg_data.get('content', '')
                                print(f"  ({ts}) {sender}: {content}")
                            print("  --- End of History ---")
                        else:
                            print("  No messages found for this server.")

                    elif action_response == "JOIN_CHALLENGE":
                        pass # Generic message already printed.

                    elif action_response == "CHALLENGE_ADMIN":
                        if status == "success" and data.get("challenge_id"):
                            print(f"  Challenge ID {data.get('challenge_id')} created for server '{data.get('server_name')}'.")

                    elif action_response == "GET_SERVER_MEMBERS":
                        if status == "success":
                            server_name_from_resp = data.get("server_name", f"ID {data.get('server_id')}")
                            members = data.get("members", [])
                            print(f"  --- Users in Server: '{server_name_from_resp}' ---")
                            if members:
                                for member in members:
                                    online_status = "Online" if member.get('is_online') else "Offline"
                                    admin_indicator = "(Admin)" if member.get('is_admin') else ""
                                    print(f"    - {member.get('username', 'Unknown')} (ID: {member.get('user_id')}) - {online_status} {admin_indicator}".strip())
                            else:
                                print("  No members found in this server.")

            elif response_data.get("type") == "MINIGAME_INVITE": # <<< MODIFIED HANDLER
                        payload = response_data.get("payload", {})
                        server_name = payload.get('server_name', 'Unknown Server')
                        minigame_ip = payload.get('minigame_ip')
                        minigame_port = payload.get('minigame_port')
                        all_participants = payload.get('all_participants', [])

                        # Clear line before printing
                        sys.stdout.write('\r' + ' ' * (prompt_len + 100) + '\r')

                        print(f"\n--- MINIGAME INVITE for Server '{server_name}'! ---")
                        print(f"  Challenge ID: {payload.get('challenge_id')}")
                        print(f"  Connect to Minigame Server at: IP={minigame_ip}, Port={minigame_port}")
                        print(f"  Game Type: {payload.get('game_type', 'N/A')}")
                        print(f"  Participants: {', '.join(all_participants)}")

                        # Check if I am a participant
                        my_username = authenticated_user_details['username'] if authenticated_user_details else None
                        if my_username and my_username in all_participants:
                            print(f"  --- You are {my_username}! Launching your minigame client... ---")
                            try:
                                game_command = [
                                    GODOT_EXECUTABLE_PATH,
                                    "--player",
                                    f"--ip={minigame_ip}",
                                    f"--name={my_username}"
                                ]
                                print(f"CLIENT: Launching game: {' '.join(game_command)}")
                                # Use Popen - this will run in the background.
                                subprocess.Popen(
                                    game_command,
                                    cwd=os.path.dirname(GODOT_EXECUTABLE_PATH) or '.'
                                )
                            except FileNotFoundError:
                                print(f"ERROR: Godot executable not found at {GODOT_EXECUTABLE_PATH}. Cannot join game.")
                            except Exception as e_game_launch:
                                print(f"ERROR: Failed to launch game client: {e_game_launch}")
                        else:
                             print(f"  --- You are not a participant ({my_username}). ---")

                        # Reprint prompt after printing invite
                        sys.stdout.write(get_prompt())
                        sys.stdout.flush()
                        continue # Skip default prompt print at end


            elif response_data.get("type") == "YOU_WERE_KICKED": # <<< NEW BROADCAST TYPE HANDLER
                payload = response_data.get("payload", {})
                server_name = payload.get('server_name', 'a server')
                kicked_by = payload.get('kicked_by_username', 'the admin')

                # Clear the current input line
                prompt_len = len(get_prompt()) # Make sure get_prompt() is defined
                sys.stdout.write('\r' + ' ' * (prompt_len + 100) + '\r')

                print(f"ALERT: You have been kicked from server '{server_name}' by Admin {kicked_by}.")

                sys.stdout.write(get_prompt()) # Re-print prompt
                sys.stdout.flush()
                continue

            elif response_data.get("type") == "CHAT_MESSAGE":
                payload = response_data.get("payload", {})
                sender = payload.get("sender_username", "Unknown")
                msg_text = payload.get("message", "")
                message_server_id = payload.get("server_id")
                message_server_name = payload.get("server_name", f"ServerID_{message_server_id}")
                ts = format_timestamp(payload.get('timestamp'))

                print(f"({message_server_id}) [{ts}] {sender}: {msg_text}")

            elif response_data.get("type") == "USER_JOINED":
                payload = response_data.get("payload", {})
                print(f"SERVER: {payload.get('username')} joined the chat system.")
            elif response_data.get("type") == "USER_LEFT":
                payload = response_data.get("payload", {})
                print(f"SERVER: {payload.get('username')} (ID: {payload.get('user_id')}) left the chat system.")

            elif status == "error" and not action_response:
                 print(f"SERVER ERROR: {message}")

            else:
                 if not action_response:
                    print(f"SERVER MSG: {message or response_data}")

            sys.stdout.write(get_prompt())
            sys.stdout.flush()

        except Exception as e:
            if running:
                print(f"\rCLIENT: Error in receiving thread: {e}")
            running = False
            break
    print("CLIENT: Receiving thread stopped.")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    if len(sys.argv) < 2:
        print("Usage: python client.py <port>")
        sys.exit(1)
    try:
        port = int(sys.argv[1])
        if not (1024 <= port <= 65535): raise ValueError("Port out of allowed range 1024-65535")
    except ValueError as e:
        print(f"Invalid port: {e}")
        sys.exit(1)

    server_ip = '127.0.0.1'
    s = socket.socket()
    s.settimeout(10.0)

    try:
        print(f"CLIENT: Connecting to {server_ip}:{port}...")
        s.connect((server_ip, port))
        print("CLIENT: Connected to server!")
    except socket.timeout:
        print(f"CLIENT: Connection attempt to server timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"CLIENT: Failed to connect: {e}")
        sys.exit(1)

    s.settimeout(None)
    while not authenticated_user_details and running:
        action_choice = input("CLIENT: (L)ogin or (R)egister? ").upper()
        if not action_choice: continue

        username = input("CLIENT: Username: ")
        if not username: continue

        password = getpass.getpass("CLIENT: Password: ")
        if not password: continue

        request_auth = None
        if action_choice == 'R':
            request_auth = {"action": "REGISTER", "payload": {"username": username, "password": password}}
        elif action_choice == 'L':
            request_auth = {"action": "LOGIN", "payload": {"username": username, "password": password}}
        else:
            print("CLIENT: Invalid choice. Please enter 'L' or 'R'.")
            continue

        if not send_json_client(s, request_auth):
            print("CLIENT: Failed to send authentication request. Exiting.")
            running = False; break

        s.settimeout(5.0)
        response_auth = receive_json_client(s)
        s.settimeout(None)

        if response_auth is None:
            print("CLIENT: Did not receive authentication response from server or connection lost.")
            running = False; break

        print(f"CLIENT: Server Auth Response: {response_auth.get('message', 'No message.')} (Status: {response_auth.get('status')})")

        if response_auth.get("status") == "success" and response_auth.get("action_response_to") == "LOGIN":
            authenticated_user_details = response_auth.get("data")
            if not authenticated_user_details or 'username' not in authenticated_user_details:
                print("CLIENT: Login success but user details missing. Exiting.")
                running = False; break
            current_server_context_name = "Global"
            client_active_server_id = None
            print(f"CLIENT: Login successful as {authenticated_user_details['username']}!")
            break
        elif response_auth.get("status") == "success" and response_auth.get("action_response_to") == "REGISTER":
            print("CLIENT: Registration successful. Please login.")
        elif response_auth.get("status") == "error":
             pass

    if authenticated_user_details and running:
        print(f"\n--- Welcome {authenticated_user_details['username']}! ---")

        sending_thread = threading.Thread(target=sendingThread, args=(s,))
        receiving_thread = threading.Thread(target=receivingThread, args=(s,))

        sending_thread.daemon = True
        receiving_thread.daemon = True

        sending_thread.start()
        receiving_thread.start()

        # <<< MODIFIED: Use a running flag and join threads for cleaner exit >>>
        try:
            while running:
                time.sleep(0.5) # Main thread can sleep
                if not sending_thread.is_alive() or not receiving_thread.is_alive():
                     print("CLIENT: A thread has exited. Shutting down.")
                     running = False # Signal other threads
                     break
        except KeyboardInterrupt:
            print("\nCLIENT: Ctrl+C detected in main loop. Shutting down.")
            running = False
            # Try to send disconnect, but don't block/error if socket is dead
            if s and not getattr(s, '_closed', True):
                 try:
                     send_json_client(s, {"action": "DISCONNECT"})
                 except: pass


        print("CLIENT: Main loop finished. Joining threads...")
        # Give threads a chance to finish based on 'running' flag
        if sending_thread.is_alive(): sending_thread.join(timeout=2.0)
        if receiving_thread.is_alive(): receiving_thread.join(timeout=2.0)

    print("CLIENT: Disconnected.")
    if s and not getattr(s, '_closed', True): # Check if socket exists and not closed
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError: pass
        s.close()