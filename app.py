# app.py
import ui.startpage.start_classes as start_page
import ui.mainpage.main_page as main_page
from ui.mainpage.mainbar_widgets import Chat
from ui.mainpage.group_widgets import Group
import json
import time
import struct
import threading
import os
import sys
import platform
import socket
import subprocess # <<< ADDED
from datetime import datetime
from PySide6.QtCore import (Signal)
from PySide6.QtWidgets import (
    QStackedWidget,
    QMainWindow,
    QApplication,
    QWidget
)
from PySide6.QtGui import (
    QIcon,
    QFontDatabase,
    Qt
)

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

# Network-related constants
MSG_LENGTH_PREFIX_FORMAT = '!I'  # Network byte order, Unsigned Integer (4 bytes)
MSG_LENGTH_PREFIX_SIZE = struct.calcsize(MSG_LENGTH_PREFIX_FORMAT)

# Get the correct path
GODOT_EXECUTABLE_PATH = get_godot_executable_path()

users = { "juan" : "123",
         "lucas" : "234"}


def format_timestamp(unix_ts):
    """Helper to format Unix timestamp into a readable string."""
    if unix_ts is None:
        return ""
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(unix_ts)))
    except:
        return str(unix_ts) # Fallback


class MainWindow(QMainWindow):
    serversReceived = Signal(list)  # Signal carrying a list of servers
    messageReceived = Signal(list)
    messageHistory = Signal(int, list)
    onlineUsers = Signal(list, int)
    modifyUserStatus = Signal(str, bool)
    onlineCount = Signal(int, int)


    def __init__(self, sock):
        super().__init__()
        self.setWindowTitle("Chat.io 👑")
        self.setGeometry(300, 90, 900, 600)
        self.setMinimumSize(900,500)

        self.m_challengeClickable = True

        self.m_socket = sock
        self.m_receiving_thread = threading.Thread(target=self.receivingThread)
        self.m_receiving_thread.daemon = True

        self.m_stack = QStackedWidget()
        self.m_start_page = start_page.StartPage()
        self.m_main_page = main_page.MainPage()

        self.m_stack.addWidget(self.m_start_page)  #j index 0
        self.m_stack.addWidget(self.m_main_page)   # index 1

        self.setCentralWidget(self.m_stack)

        # Handle register signal
        self.m_start_page.m_registerSection.m_buttonContainer.m_registerButton.clicked.connect(self.handleRegister)
        self.m_start_page.m_registerSection.m_repeatPasswordInput.returnPressed.connect(self.handleRegister)
        # Handle login signal
        self.m_start_page.m_loginSection.m_buttonContainer.m_loginButton.clicked.connect(self.handleLogin)
        self.m_start_page.m_loginSection.m_passwordInput.returnPressed.connect(self.handleLogin)

        self.m_main_page.m_mainBar.m_addGroups.m_createGroupForm.m_send.clicked.connect(lambda: self.sendRequest("/create_server "+self.m_main_page.m_mainBar.m_addGroups.m_createGroupForm.m_groupName.text()))

        self.m_main_page.m_mainBar.m_addGroups.m_joinGroupForm.m_send.clicked.connect(lambda: self.sendRequest("/join_server "+self.m_main_page.m_mainBar.m_addGroups.m_joinGroupForm.m_groupName.text()))


        self.serversReceived.connect(self.getMyServers)
        self.messageReceived.connect(self.displayMessage)
        self.messageHistory.connect(self.loadHistory)
        self.onlineUsers.connect(self.showUsers)
        self.modifyUserStatus.connect(self.changeUserStatus)
        self.onlineCount.connect(self.updateOnlineCount)


    def updateOnlineCount(self, userCount, serverID):
        # ... (existing code) ...
        groupID = self.m_main_page.m_serverIDtoGroupBarIndex[serverID]
        group = self.m_main_page.m_mainBar.m_groupBar.m_groups[groupID]
        group.m_groupInfo.updateCount(userCount)


    def changeUserStatus(self, username, flag):
        # ... (existing code) ...
        for key in self.m_main_page.m_chatsContainer.m_chats:
            chat = self.m_main_page.m_chatsContainer.m_chats[key]
            if username in chat.m_members:
                print(f"{username} belongs to {chat.m_chatID}")
                chat.changeMemberStatus(username, flag)
                self.updateOnlineCount(chat.m_onlineCount, chat.m_chatID)


    def showUsers(self, list, serverID):
        # ... (existing code) ...
        chat = self.m_main_page.m_chatsContainer.m_chats[serverID]
        # Clear previous members
        chat.m_members.clear()
        members_container = chat.m_groupDescription.m_membersBar.m_membersContainer
        members_info = members_container.m_membersInfo

        # Clear member widgets from layout
        layout = members_container.m_layout
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                layout.removeWidget(widget)
                widget.setParent(None)

        members_info.clear()
        chat.m_onlineCount = 0

        for member in list:
            username = member.get('username', 'Unknown')
            user_id = member.get('user_id')
            online = member.get('is_online')
            admin_indicator = "admin" if member.get('is_admin') else "user"
            inputBar = chat.m_chatView.m_inputMessageBar
            #s
            inputBar.m_challengeButton.setStyleSheet("""
                            QPushButton {
                                border-radius: 10px;
                                padding: 7px;
                                border: 1px solid #1f252d;
                            }

                            QPushButton:focus {
                                    border: 1px solid grey;
                                    outline: none;
                                }

                            QPushButton:hover {
                                background-color: #2a313c;
                            } """)

            if username==self.m_username:
                chat.m_isAdmin = member.get('is_admin')
                if admin_indicator=="user":
                    inputBar.m_challengeButton.clicked.connect(lambda event, sid=serverID: self.sendChallengeRequest(sid)) # <<< Pass serverID

                    inputBar.m_challengeButton.setIcon(QIcon(os.path.join("assets","icons","Interface-Essential-Crown--Streamline-Pixel.svg")))

                    inputBar.m_challengeButton.setCursor(Qt.PointingHandCursor)
                else:
                    inputBar.m_challengeButton.setIcon(QIcon(os.path.join("assets","icons","Interface-Essential-Crown--Streamline-Pixel-grey.svg")))



            chat.addMember(username, user_id, admin_indicator, online)

            if (online):
                chat.m_onlineCount+=1
                self.updateOnlineCount(chat.m_onlineCount, serverID)


    def sendChallengeRequest(self, serverID):
        self.sendRequest(f"/challenge_server_admin {serverID}")

    # <<< Add this method >>>
    def acceptChallengeRequest(self, serverID):
        print("HELLO")
        print(f"CLIENT: Attempting to accept challenge for server ID: {serverID}")
        self.sendRequest(f"/accept_challenge {serverID}")

    # <<< Add this method >>>
    def joinChallengeRequest(self, serverID):
        print(f"CLIENT: Attempting to join challenge for server ID: {serverID}")
        self.sendRequest(f"/join_challenge {serverID}")


    def deleteHistory(self, server_id):
        # ... (existing code) ...
        container = self.m_main_page.m_chatsContainer.m_chats[server_id].m_chatView.m_chatArea.m_container_layout

        for child in container.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            child.setParent(None)
            child.deleteLater()


    def loadHistory(self, server_id, list):
        # ... (existing code) ...
        self.deleteHistory(server_id)
        for msg_data in list:
            ts = format_timestamp(msg_data.get('timestamp'))
            sender = msg_data.get('sender_username', 'Unknown')
            content = msg_data.get('content', '')
            print(f"  ({ts}) {sender}: {content}")
            self.displayMessage([server_id,ts,sender,content])
        print("  --- End of History ---")


    def handleRegister(self):
        # ... (existing code) ...
        register_sect = self.m_start_page.m_registerSection

        username = register_sect.m_userInput.text()
        password = register_sect.m_passwordInput.text()
        rep_password = register_sect.m_repeatPasswordInput.text()

        if password and username:
            if (password == rep_password):
                if (self.handleAuth(username, password, "R")):
                    self.m_start_page.switch_layout(0)
            else:
                self.m_start_page.set_warning(0, "Passwords do not match.")


    def handleLogin(self):
        # ... (existing code) ...
        login_sect = self.m_start_page.m_loginSection

        username = login_sect.m_userInput.text()
        password = login_sect.m_passwordInput.text()

        if (username and password):
            if (self.handleAuth(username, password, "L")):
                self.m_receiving_thread.start()
                self.sendRequest("/my_servers")
                self.switch_layout()


    def getMyServers(self, servers):
        # ... (existing code) ...
        groupBar = self.m_main_page.m_mainBar.m_groupBar
        chatContainer = self.m_main_page.m_chatsContainer

        # --- Clear existing chat widgets ---
        for chat in chatContainer.m_chats.values():
            chatContainer.m_stack.removeWidget(chat)
            chat.deleteLater()
        chatContainer.m_chats.clear()
        self.m_main_page.serverIDtoIndex.clear()

        # --- Clear sidebar UI ---
        while groupBar.m_container_layout.count():
            item = groupBar.m_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        groupBar.m_groups.clear()
        self.m_main_page.m_serverIDtoGroupBarIndex.clear()

        # --- Rebuild from server list ---
        for server_item in servers:
            isAdmin = self.m_username == server_item.get('admin_username', 'N/A')
            self.addGroup(server_item.get('name'), server_item.get('server_id'), server_item.get('invite_code'), isAdmin)


    def sendMessage(self, ChatID):
        # ... (existing code) ...
        text = self.m_main_page.m_chatsContainer.m_chats[ChatID].m_chatView.m_inputMessageBar.m_inputBar.text()
        #/message <id> <message>
        self.sendRequest(f"/message {ChatID} {text}")
        self.m_main_page.m_chatsContainer.m_chats[ChatID].m_chatView.m_inputMessageBar.m_inputBar.setText("")


    def displayMessage(self, list):
        global authenticated_user_details
        print(f"{self.m_userID} : {self.m_username}")
        server_id = list[0]
        timestamp = list[1]
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.strftime("%m/%d %H:%M")
        sender = list[2] # <<< Get sender
        isSender = sender == self.m_username
        text = list[3]
        print (f"{list[0]},{list[1]},{list[2]},{list[3]}")

        if server_id not in self.m_main_page.m_chatsContainer.m_chats:
            print(f"CLIENT: Received message for unknown server ID {server_id}. Ignoring for now.")
            return

        chat = self.m_main_page.m_chatsContainer.m_chats[server_id]
        is_admin = chat.m_isAdmin

        # <<< Pass server_id to add_message >>>
        chat.m_chatView.m_chatArea.add_message(sender, text, timestamp, is_admin, isSender, server_id)


    def switch_layout(self):
        # ... (existing code) ...
        self.m_stack.setCurrentIndex(not self.m_stack.currentIndex())


    def handleAuth(self, username, password, action_choice):
        # ... (existing code) ...
        request_auth = None
        if action_choice == 'R':
            request_auth = {"action": "REGISTER", "payload": {"username": username, "password": password}}
        elif action_choice == 'L':
            request_auth = {"action": "LOGIN", "payload": {"username": username, "password": password}}

        if not send_json_client(self.m_socket, request_auth):
            self.m_start_page.set_warning(0, "CLIENT: Failed to send authentication request. Exiting.")

            return 0

        self.m_socket.settimeout(5.0)
        response_auth = receive_json_client(s)
        self.m_socket.settimeout(None)

        if response_auth is None:
            self.m_start_page.set_warning(0, "CLIENT: Did not receive authentication response from server or connection lost.")
            return 0

        print(f"CLIENT: Server Auth Response: {response_auth.get('message', 'No message.')} (Status: {response_auth.get('status')})")

        if response_auth.get("status") == "success" and response_auth.get("action_response_to") == "LOGIN":
            authenticated_user_details = response_auth.get("data")
            if not authenticated_user_details or 'username' not in authenticated_user_details:
                print("CLIENT: Login success but user details missing. Exiting.")
                running = False; return
            current_server_context_name = "Global"
            client_active_server_id = None
            self.m_start_page.set_warning(1, f"CLIENT: Login successful as {authenticated_user_details['username']}!")
            self.m_username = authenticated_user_details['username']
            self.m_userID = authenticated_user_details['user_id']
            return 1
        elif response_auth.get("status") == "success" and response_auth.get("action_response_to") == "REGISTER":
            self.m_start_page.set_warning(1, "CLIENT: Registration successful. Please login.")
            return 1
        elif response_auth.get("status") == "error":
            self.m_start_page.set_warning(0, response_auth.get('message', 'No message.'))


    def sendRequest(self, request):
        # ... (existing code) ...
        sock = self.m_socket
        request_json = None
        command_processed = False

        try:

            request_json = None
            command_processed = False

            if request.startswith("/"):
                command_processed = True
                parts = request.split(maxsplit=1)
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
                        self.m_main_page.m_mainBar.m_addGroups.m_createGroupForm.warn.emit("Invalid server name", 0)

                elif command == "/list_servers":
                    request_json = {"action": "LIST_ALL_SERVERS"}

                elif command == "/my_servers":
                    request_json = {"action": "LIST_MY_SERVERS"}

                elif command == "/users_in_server": # <<< NEW COMMAND
                    target_server_id_for_request = None
                    if len(args_list) == 1: # User provided a server ID
                        try:
                            target_server_id_for_request = int(args_list[0])
                        except ValueError:
                            print("CLIENT: Invalid server ID. Must be a number.")
                    else: print("CLIENT: Usage: /users_in_server <server_id>")
                    if target_server_id_for_request is not None:
                        request_json = {"action": "GET_SERVER_MEMBERS", "payload": {"server_id": target_server_id_for_request}}

                elif command == "/join_server": # Renamed from /join_server
                    if args_str: # Expecting a single argument: the invite code
                        invite_code = args_str
                        request_json = {"action": "JOIN_SERVER", "payload": {"invite_code": invite_code}}
                    else:
                        print("CLIENT: Usage: /join_server <invite_code>")
                        self.m_main_page.m_mainBar.m_addGroups.m_joinGroupForm.warn.emit("Invalid server ID", 0)

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


            else:
                print("CLIENT: Invalid input. Type /help for commands or /message <server_id> <message> to chat.")

            if request_json:
                if not send_json_client(sock, request_json):
                    print("CLIENT: Failed to send request to server. Disconnecting.")
                    running = False
                if request_json.get("action") == "DISCONNECT":
                    running = False
        except EOFError:
            print("\nCLIENT: EOF detected. Sending disconnect.")
            running = False
            send_json_client(sock, {"action": "DISCONNECT"})
        except KeyboardInterrupt:
            print("\nCLIENT: KeyboardInterrupt. Sending disconnect.")
            running = False
            send_json_client(sock, {"action": "DISCONNECT"})
        except Exception as e:
            print(f"CLIENT: Error in sending thread: {e}")

    def receivingThread(self):
        # ... (existing code, ensure CHAT_MESSAGE handles challenge messages) ...
        sock = self.m_socket
        global running
        global authenticated_user_details
        global current_server_context_name
        global client_active_server_id

        while running:
            try:
                response_data = receive_json_client(sock)
                if response_data is None:
                    if running:
                        print("\rCLIENT: Disconnected from server (receiver).") # warning
                    running = False
                    break

                # prompt_len = len(get_prompt())
                # sys.stdout.write('\r' + ' ' * (prompt_len + 80) + '\r')

                action_response = response_data.get("action_response_to")
                status = response_data.get("status")
                message = response_data.get("message", "")
                data = response_data.get("data", {})

                if action_response:
                    print(f"SERVER ({action_response} - {status}): {message}")
                    if status == "success":
                        if action_response == "LIST_ALL_SERVERS" or action_response == "LIST_MY_SERVERS":
                            servers = data.get("servers", [])
                            self.serversReceived.emit(servers) # <----
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
                                self.m_main_page.m_mainBar.m_addGroups.m_createGroupForm.warn.emit("Group created successfully!", 1) # <----
                                self.sendRequest("/my_servers") # <----

                        elif action_response == "JOIN_SERVER":
                            self.m_main_page.m_mainBar.m_addGroups.m_joinGroupForm.warn.emit("Joined group successfully!", 1) # <----
                            self.sendRequest("/my_servers") # <----

                        elif action_response == "SERVER_HISTORY": # Ensure this part is correct from previous step
                            server_name = data.get("server_name", "UnknownServer")
                            messages_history = data.get("messages", [])
                            print(f"  --- Message History for '{server_name}' (ID: {data.get('server_id')}) ---")
                            if messages_history: # <----
                                self.messageHistory.emit(data.get('server_id'),messages_history) # <----
                            else:
                                print("  No messages found for this server.")

                        elif action_response == "JOIN_CHALLENGE":
                            # The main message from the server ("You have successfully joined..." or error)
                            # is already printed by the generic response handler part:
                            # print(f"SERVER ({action_response} - {status}): {message}")
                            # No additional data payload expected for this specific response from server for now.
                            print(f"SERVER: {message}") # <<< Print the server message
                            pass # Generic message already printed.

                        elif action_response == "ACCEPT_CHALLENGE":
                            print(f"SERVER: {message}") # <<< Print the server message

                        elif action_response == "CHALLENGE_ADMIN":
                            # The main message from the server ("Challenge initiated..." or error)
                            # is already printed by the generic response handler.
                            # If successful, 'data' might contain challenge_id.
                            if status == "success" and data.get("challenge_id"):
                                print(f"  Challenge ID {data.get('challenge_id')} created for server '{data.get('server_name')}'.")
                            # Additional specific display logic for this response if needed.

                        elif action_response == "GET_SERVER_MEMBERS":
                            if status == "success":
                                server_name_from_resp = data.get("server_name", f"ID {data.get('server_id')}")
                                members = data.get("members", [])
                                print(f"  --- Users in Server: '{server_name_from_resp}' ---")
                                if members:
                                    print(f"SERVER ID IS: {data.get('server_id')}")
                                    self.onlineUsers.emit(members, data.get('server_id')) # <----
                                    for member in members:
                                        online_status = "Online" if member.get('is_online') else "Offline"
                                        admin_indicator = "(Admin)" if member.get('is_admin') else ""
                                        print(f"    - {member.get('username', 'Unknown')} (ID: {member.get('user_id')}) - {online_status} {admin_indicator}".strip())
                                else:
                                    print("  No members found in this server.")

                    elif status=="error" and action_response=="JOIN_SERVER":
                        self.m_main_page.m_mainBar.m_addGroups.m_joinGroupForm.warn.emit(message,0) # <----

                elif response_data.get("type") == "MINIGAME_INVITE": # <<< NEW BROADCAST TYPE HANDLER
                            payload = response_data.get("payload", {})
                            server_name = payload.get('server_name', 'Unknown Server')
                            minigame_ip = payload.get('minigame_ip')
                            minigame_port = payload.get('minigame_port')
                            all_participants = payload.get('all_participants', [])

                            print(f"\n--- MINIGAME INVITE for Server '{server_name}'! ---")
                            print(f"  Challenge ID: {payload.get('challenge_id')}")
                            print(f"  Connect to Minigame Server at: IP={minigame_ip}, Port={minigame_port}")
                            print(f"  Game Type: {payload.get('game_type', 'N/A')}")
                            print(f"  Participants: {', '.join(all_participants)}")
                            print(f"  --- If you are a participant, you would now launch your minigame client! ---")

                            # Check if I am a participant
                            my_username = self.m_username
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
                            #sys.stdout.write(get_prompt())
                            #sys.stdout.flush()
                            #continue # Skip default prompt print at end


                elif response_data.get("type") == "YOU_WERE_KICKED": # <<< NEW BROADCAST TYPE HANDLER
                    payload = response_data.get("payload", {})
                    server_name = payload.get('server_name', 'a server')
                    kicked_by = payload.get('kicked_by_username', 'the admin')

                    print(f"ALERT: You have been kicked from server '{server_name}' by Admin {kicked_by}.")

                    # Optional: If client was tracking an active server context, clear it
                    # global client_active_server_id, current_server_context_name
                    # if client_active_server_id == payload.get('server_id'):
                    #     print(f"CLIENT: You are no longer active in '{server_name}'.")
                    #     client_active_server_id = None
                    #     current_server_context_name = "Global" # Or some other default


                elif response_data.get("type") == "CHAT_MESSAGE":
                    payload = response_data.get("payload", {})
                    sender = payload.get("sender_username", "Unknown")
                    msg_text = payload.get("message", "")
                    message_server_id = payload.get("server_id")
                    message_server_name = payload.get("server_name", f"ServerID_{message_server_id}")
                    ts = format_timestamp(payload.get('timestamp'))

                    print(f"({message_server_id}) [{ts}] {sender}: {msg_text}")

                    self.messageReceived.emit([message_server_id, ts, sender, msg_text]) # <----
                    if (sender=="SYSTEM" or sender=="CHALLENGE_NOTICE"): # <<< Refresh users if system or challenge message
                        self.sendRequest(f"/users_in_server {message_server_id}") # <----
                        # self.onlineUsers.emit(members, message_server_id) # <---- No need to emit here, GET_SERVER_MEMBERS will do it

                elif response_data.get("type") == "USER_JOINED":
                    payload = response_data.get("payload", {})
                    # This is a global "joined the system" message, like online status.
                    # Server-specific need more context
                    print(f"SERVER: {payload.get('username')} joined the chat system.")
                    self.modifyUserStatus.emit(payload.get('username'), 1) # <----

                elif response_data.get("type") == "USER_LEFT":
                    payload = response_data.get("payload", {})
                    # This is a global "left the system" message, like offline status.
                    print(f"SERVER: {payload.get('username')} (ID: {payload.get('user_id')}) left the chat system.")
                    self.modifyUserStatus.emit(payload.get('username'), 0) # <----

                elif status == "error" and not action_response:
                    print(f"SERVER ERROR: {message}")

                else:
                    if not action_response:
                        print(f"SERVER MSG: {message or response_data}")

            except Exception as e:
                if running:
                    print(f"\rCLIENT: Error in receiving thread: {e}")
                running = False
                break
        print("CLIENT: Receiving thread stopped.")


    def addGroup(self, name, chatID, inviteCode, isAdmin):
        group = Group(name, chatID)
        group.clicked.connect(lambda: self.switchChat(group))
        self.m_main_page.m_mainBar.m_groupBar.m_groups.append(group)
        self.m_main_page.m_mainBar.m_groupBar.m_container_layout.addWidget(group)
        groupIndex = self.m_main_page.m_mainBar.m_groupBar.m_container_layout.indexOf(group)
        self.m_main_page.m_serverIDtoGroupBarIndex[chatID] = groupIndex

        new_chat = Chat(name, chatID, isAdmin)
        self.m_main_page.m_chatsContainer.m_chats[chatID] = new_chat
        new_chat.m_chatView.m_inputMessageBar.m_inputBar.returnPressed.connect(lambda: self.sendMessage(new_chat.m_chatID))
        self.m_main_page.m_chatsContainer.m_stack.addWidget(new_chat)
        chatIndex = self.m_main_page.m_chatsContainer.m_stack.indexOf(new_chat)
        new_chat.m_groupDescription.m_membersBar.m_leaveGroupButton.clicked.connect(lambda: self.leaveGroup(new_chat.m_chatID))

        # <<< Connect signals here >>>
        new_chat.m_chatView.m_chatArea.acceptChallenge.connect(self.acceptChallengeRequest)
        new_chat.m_chatView.m_chatArea.joinChallenge.connect(self.joinChallengeRequest)


        self.m_main_page.serverIDtoIndex[chatID] = chatIndex
        self.sendRequest(f"/server_history {chatID}")
        self.sendRequest(f"/users_in_server {chatID}")

        new_chat.m_groupDescription.m_membersBar.m_groupInviteContainer.m_groupInvitationID.setText(inviteCode)


    def leaveGroup(self, groupID):
        # ... (existing code) ...
        self.sendRequest(f"/leave_server {groupID}")
        self.sendRequest("/my_servers")


    def switchChat(self, group):
        # ... (existing code) ...
        self.m_main_page.m_chatsContainer.m_stack.setCurrentIndex(self.m_main_page.serverIDtoIndex[group.m_chatID])
        for g in self.m_main_page.m_mainBar.m_groupBar.m_groups:
            g.setSelected(g == group)

# ... (send_json_client, receive_all, receive_json_client functions) ...
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
client_active_server_id = None # <<<< NEW: Stores the ID of the server client is currently in


if __name__ == "__main__":

    os.system('cls' if os.name == 'nt' else 'clear')

    # if len(sys.argv) < 2:
    #     print("Usage: python client.py <port>")
    #     sys.exit(1)
    try:
        # port = int(sys.argv[1])
        port = 1235
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


    app = QApplication(sys.argv)
    window = MainWindow(s)

    font_id = QFontDatabase.addApplicationFont(os.path.join("assets", "fonts", "Minecraft.ttf"))
    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

    app.setStyleSheet("QWidget { font-family: Minecraft; font-size: 16px;}")
    appIcon = QIcon(os.path.join("assets","icons","Interface-Essential-Crown--Streamline-Pixel.svg"))
    app.setWindowIcon(appIcon)

    s.settimeout(None)



    window.show()
    sys.exit(app.exec())