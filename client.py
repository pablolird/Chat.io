import socket
import os
import threading
import sys
import getpass # To hide password input
import json
import time

def send_json_client(sock, data_dict):
    try:
        message = json.dumps(data_dict)
        sock.sendall(message.encode('utf-8'))
        return True
    except Exception as e:
        print(f"CLIENT: Error sending JSON: {e}")
        return False

def receive_json_client(sock):
    try:
        data_bytes = sock.recv(1024)
        if not data_bytes: return None
        return json.loads(data_bytes.decode('utf-8'))
    except json.JSONDecodeError:
        print("CLIENT: Received malformed JSON from server.")
        return {"status": "error", "message": "Malformed JSON from server."} # Or handle differently
    except ConnectionResetError:
        print("CLIENT: Connection reset by server during receive.")
        return None
    except Exception as e:
        print(f"CLIENT: Error receiving JSON: {e}")
        return None

running = True # Global flag for threads
authenticated_user_details = None # Store {'user_id': id, 'username': name}

def sendingThread(sock): # No longer needs username passed, gets from global
    global running
    global authenticated_user_details
    
    print(f"--- You are logged in as {authenticated_user_details['username']}. Type your message or 'close' to disconnect. ---")
    while running:
        try:
            message_text = input() # Get raw message text
            if not running: break # Check flag again, in case changed by receiving thread

            if message_text.lower() == "close":
                print("CLIENT: Sending disconnect signal...")
                disconnect_request = {"action": "DISCONNECT"}
                if send_json_client(sock, disconnect_request):
                    print("CLIENT: Disconnect signal sent.")
                else:
                    print("CLIENT: Failed to send disconnect signal.")
                running = False # Signal other thread and main to stop
                break
            else:
                # Send as a chat message
                chat_request = {
                    "action": "SEND_CHAT_MESSAGE",
                    "payload": {"message": message_text}
                }
                if not send_json_client(sock, chat_request):
                    print("CLIENT: Failed to send chat message. Disconnecting.")
                    running = False
                    break
        except EOFError: # Happens if input stream is closed (e.g. piping input)
            print("CLIENT: Input stream closed. Disconnecting.")
            running = False
            # Attempt to send disconnect to server
            if send_json_client(sock, {"action": "DISCONNECT"}):
                 print("CLIENT: Disconnect signal sent due to EOF.")
            break
        except Exception as e:
            print(f"CLIENT: Error in sending thread: {e}")
            running = False
            break
    print("CLIENT: Sending thread stopped.")

def receivingThread(sock):
    global running
    while running:
        try:
            response_data = receive_json_client(sock)
            if response_data is None: # Connection closed or major error
                print("CLIENT: Disconnected from server (receive_json returned None).")
                running = False
                break

            print(f"CLIENT DEBUG: Raw received: {response_data}") # For debugging

            if response_data.get("type") == "NEW_CHAT_MESSAGE":
                payload = response_data.get("payload", {})
                sender = payload.get("sender_username", "Unknown")
                message = payload.get("message", "")
                # Simple display, clear previous input line if possible
                # This \r and end='' trick works well in many terminals
                print(f"\r{sender}: {message}\n> ", end="") 
            elif response_data.get("type") == "USER_JOINED":
                payload = response_data.get("payload", {})
                print(f"\rSERVER: {payload.get('username')} joined the chat.\n> ", end="")
            elif response_data.get("type") == "USER_LEFT":
                payload = response_data.get("payload", {})
                print(f"\rSERVER: {payload.get('username')} left the chat.\n> ", end="")
            elif response_data.get("status") == "error": # General error from server
                print(f"\rSERVER ERROR: {response_data.get('message', 'Unknown error.')}\n> ", end="")
            # Add more handlers for other broadcast types or specific responses if needed
            else:
                # Could be other responses not directly handled here (e.g. from future commands)
                print(f"\rSERVER MSG: {response_data}\n> ", end="")


        except Exception as e:
            print(f"CLIENT: Error in receiving thread: {e}")
            running = False # Stop on error
            break
    print("CLIENT: Receiving thread stopped.")


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    # ... (port and server_ip setup as before) ...
    if len(sys.argv) < 2:
        print("Usage: python client.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])
    server_ip = '127.0.0.1'
    s = socket.socket()
    try:
        s.connect((server_ip, port))
        print("CLIENT: Connected to server!")
    except Exception as e:
        print(f"CLIENT: Failed to connect: {e}")
        sys.exit(1)

    # Authentication Loop
    while not authenticated_user_details:
        action_choice = input("CLIENT: (L)ogin or (R)egister? ").upper()
        username = input("CLIENT: Username: ")
        password = getpass.getpass("CLIENT: Password: ")

        if not username or not password:
            print("CLIENT: Username and password cannot be empty.")
            continue
        
        request = None
        if action_choice == 'R':
            request = {"action": "REGISTER", "payload": {"username": username, "password": password}}
        elif action_choice == 'L':
            request = {"action": "LOGIN", "payload": {"username": username, "password": password}}
        else:
            print("CLIENT: Invalid choice.")
            continue

        if not send_json_client(s, request):
            print("CLIENT: Failed to send auth request. Exiting.")
            s.close()
            sys.exit(1)

        response = receive_json_client(s)
        if response is None:
            print("CLIENT: Did not receive auth response from server. Exiting.")
            s.close()
            sys.exit(1)

        print(f"CLIENT: Server Auth Response: {response.get('message', 'No message.')} (Status: {response.get('status')})")

        if response.get("status") == "success" and response.get("action_response_to") == "LOGIN":
            authenticated_user_details = response.get("data") # Should contain user_id, username
            print(f"CLIENT: Login successful. Welcome {authenticated_user_details['username']}!")
            break 
        elif response.get("status") == "success" and response.get("action_response_to") == "REGISTER":
            print("CLIENT: Registration successful. Please login.") # Or auto-login if server supports
        elif response.get("status") == "error":
            print(f"CLIENT: Auth Error: {response.get('message', 'Unknown error from server.')}")
            # Loop continues for retry
        else:
            print(f"CLIENT: Unexpected auth response: {response}")


    if authenticated_user_details:
        running = True
        # Add a small delay for auth messages to clear if needed, or improve prompt handling
        # time.sleep(0.1) 
        print("\n> ", end="") # Initial prompt for chat after login

        sending_thread = threading.Thread(target=sendingThread, args=(s,))
        receiving_thread = threading.Thread(target=receivingThread, args=(s,))

        sending_thread.start()
        receiving_thread.start()

        sending_thread.join()
        # When sending_thread stops (e.g. user types 'close'), 'running' becomes False.
        # We need to ensure receiving_thread also stops.
        if receiving_thread.is_alive():
            print("CLIENT: Attempting to shutdown receiving thread...")
            # A more robust way to stop a blocking recv() is to close the socket from another thread.
            # Since 'running' is False, the recv loop should exit on next iteration or error.
            # Forcibly closing socket if client initiated 'close'
            try:
                s.shutdown(socket.SHUT_RDWR) # Signal server no more data, and stop receiving
            except: pass # Ignore if already closed
            s.close() # Close our end
            receiving_thread.join(timeout=2.0) # Wait a bit for it to exit
            if receiving_thread.is_alive():
                print("CLIENT: Receiving thread did not stop gracefully.")
    
    print("CLIENT: Disconnected.")
    if not s._closed: # Check if socket is not already closed
        s.close()