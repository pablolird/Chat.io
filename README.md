<p align="center">
<img src="https://github.com/user-attachments/assets/70b6ef36-cbce-462a-9c87-9fa2df3b5650" alt="logo" width="400"/>
</p>

![GitHub Created At](https://img.shields.io/github/created-at/pablolird/Chat.io)
![GitHub contributors](https://img.shields.io/github/contributors/pablolird/Chat.io)

---
![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=for-the-badge)
![SQLite Badge](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=fff&style=for-the-badge)
![PySide Badge](https://img.shields.io/badge/PySide-41CD52?logo=qt&logoColor=fff&style=for-the-badge)
![Godot Engine Badge](https://img.shields.io/badge/Godot%20Engine-478CBF?logo=godotengine&logoColor=fff&style=for-the-badge)
![MongoDB Badge](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=fff&style=for-the-badge)

# Chat.io - A Real-Time Chat Application with Minigames

**Chat.io** is a dynamic, multi-user chat application that enables users to connect to various servers, engage in real-time messaging, and challenge the admin in exciting minigames developed with the Godot Engine to become new leader of the group. The application features a robust client-server architecture, user authentication, and a rich graphical user interface built with PySide6.

---

## 🌟 Features

* **User Authentication**: Secure registration and login system for users.
* **Real-Time Messaging**: Instantaneous message exchange within designated chat servers.
* **Server Management**:
    * Create new chat servers with unique invite codes.
    * Join existing servers using invite codes.
    * Leave servers.
    * List all available servers and servers the user is a member of.
* **Admin Controls**:
    * Server administrators can kick users from their server.
    * Automatic admin reassignment if the current admin leaves.
* **Message History**: View recent messages for a server.
* **User Presence**: See who's online in a server, including their admin status.
* **Minigame Integration**:
    * Users can challenge the server admin to a minigame.
    * Admins can accept incoming challenges.
    * Other server members can join an active, pending challenge.
    * Automatic launch of the Godot game client and server instances.
    * The winner of the minigame is detected, announced, and promoted to server admin.
* **Graphical User Interface (GUI)**: Intuitive and responsive UI developed using PySide6.
* **Cross-Platform Game Executables**: Godot game exports for Windows and Linux included.
* **(Optional) Message Logging**: Server-side logging of message traffic to MongoDB.

---

## 🛠️ Technologies Used

* **Backend**: Python
* **Frontend/GUI**: Python with PySide6
* **Networking**: Python `socket` module (TCP/IP)
* **Database**:
    * SQLite: For core application data (users, servers, messages, challenges).
    * MongoDB: For optional server-side message traffic logging.
* **Minigame Engine**: Godot Engine
* **Serialization**: JSON for client-server communication.

---

## 📂 Project Structure
```
Chat-App---Final-Project/
│
├── app.py                     # Main PySide6 GUI application & client logic
├── client.py                  # Standalone command-line client (optional use)
├── server.py                  # Server-side application logic
├── database.py                # SQLite database interactions
├── chat_app.db                # SQLite database file (generated)
├── test.py                    # Utility script (OS detection, paths)
│
├── ui/                        # PySide6 UI components
│   ├── startpage/             # Login/Registration UI modules
│   └── mainpage/              # Main chat interface UI modules
│
├── GodotGame/                 # Godot minigame project and exports
│   ├── FinalLinux.sh          # Linux game launcher script
│   ├── FinalLinux.x86_64      # Linux game executable
│   ├── FinalWindows.exe       # Windows game executable (assumed from server.py)
│   └── export_presets.cfg     # Godot export configuration
│
└── assets/                    # Icons, fonts, and other static resources
├── icons/
├── fonts/
└── user-icons/
```
---

## 🚀 Setup and Installation

### Prerequisites
* Python 3.x
* PySide6
* (Optional) MongoDB: If you want to use the message logging feature.
* Godot Engine (only if you intend to modify or re-export the minigame)

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/pablolird/Chat.io.git](https://github.com/pablolird/Chat.io.git)
    cd Chat.io
    ```

2.  **Install Dependencies:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install PySide6 pymongo # pymongo is optional
    ```
    *(If a `requirements.txt` file is created, users can run `pip install -r requirements.txt`)*

3.  **Database Initialization:**
    * The SQLite database (`chat_app.db`) is created and initialized automatically when you first run `server.py`.
    * If using MongoDB for logging, ensure your MongoDB instance is running and accessible. The server will attempt to connect to `mongodb://localhost:27017/`.

4.  **Godot Game Executables:**
    * The pre-built game executables (`FinalLinux.x86_64` and `FinalWindows.exe`) are expected to be in the `GodotGame/` directory.
    * Ensure `FinalLinux.x86_64` (and `FinalLinux.sh`) have execute permissions on Linux systems:
        ```bash
        chmod +x GodotGame/FinalLinux.x86_64
        chmod +x GodotGame/FinalLinux.sh
        ```
    * The paths to these executables are determined dynamically in `app.py` and `server.py` based on the operating system.

5.  **Running the Server:**
    Open a terminal and run:
    ```bash
    python server.py <port_number>
    ```
    Example: `python server.py 1235`

6.  **Running the Client (GUI Application):**
    Open another terminal (and activate the virtual environment if you used one) and run:
    ```bash
    python app.py
    ```
    The application will attempt to connect to the server IP `192.168.50.91` and port `1235` as hardcoded in `app.py`. You may need to adjust this in `app.py` if your server is running on a different IP or you used a different port.

---

## 🎮 How to Use

### GUI Application (`app.py`)

1.  **Launch `app.py`**.
2.  **Register/Login**:
    * If you're a new user, use the registration form to create an account.
    * Existing users can log in with their credentials.
3.  **Main Interface**:
    * **Sidebar**: Use the sidebar buttons to switch between viewing your groups and adding/joining new groups.
    * **Create Group**: Navigate to the "add groups" section and use the "Create group" form.
    * **Join Group**: Use the "Join existing group" form with an invite code.
    * **Select Chat**: Click on a group in the "GroupBar" to open its chat view.
    * **Send Messages**: Type your message in the input bar at the bottom of the chat view and press Enter.
    * **View Group Info/Members**: Click on the group name banner at the top of the chat view to see group details and members. You can also find the invite code and leave the group from this view.
4.  **Minigames**:
    * **Challenge Admin**: If you are not the admin of a server, a button (often styled with a crown icon) will be available in the message input bar. Click this to challenge the current server admin.
    * **Challenge Notification**: A "CHALLENGE_NOTICE" message will appear in the chat.
    * **Accept Challenge**: If you are the admin and have been challenged, the "CHALLENGE_NOTICE" message will have an "Accept Challenge" button. Click it to start the game.
    * **Join Challenge**: If you are a regular member in a server where a challenge has been initiated but not yet accepted, the "CHALLENGE_NOTICE" message will have a "Join Challenge" button. Click this to participate (up to `MAX_CHALLENGE_PARTICIPANTS`, typically 4).
    * **Game Launch**: Once the admin accepts, the Godot game server will start, and participants' game clients will launch automatically, connecting them to the minigame.
    * **Winner**: After the game, the winner is announced in chat, and they become the new server admin.

---

## ⚙️ Configuration

* **Server IP Address**:
    * The server (`server.py`) currently binds to `192.168.50.91`. For local testing on a single machine, you can change this to `127.0.0.1`. For access across your local network, change it to `0.0.0.0` or your machine's specific LAN IP.
    * The client application (`app.py`) attempts to connect to `192.168.50.91`. This must match the server's IP address.
* **Port Number**:
    * Passed as a command-line argument to `server.py`.
    * Hardcoded as `1235` in `app.py`. This must match the port used by the server.
* **Godot Executable Paths**:
    * The paths are determined dynamically in `app.py` and `server.py` using the `get_godot_executable_path()` function, which checks the OS. Ensure the executables are in the `GodotGame/` directory.
* **MongoDB URI**:
    * Hardcoded in `server.py` as `mongodb://localhost:27017/` for the `chat_app_logs` database. Modify if your MongoDB instance is different.
* **SQLite Database File**:
    * Defined as `DATABASE_FILE = 'chat_app.db'` in `database.py`.

---

## 💡 How Minigames Work (Technical Flow)

1.  A user (non-admin) in a server initiates a challenge against the current server admin via the GUI. This sends a `/challenge_server_admin <server_id>` request.
2.  The server receives this, validates it, and if valid, creates a "challenge" entry in the database with a 'pending' status. It then broadcasts a "CHALLENGE_NOTICE" message to the server, including buttons for the admin to "Accept" and for other users to "Join".
3.  The admin can click "Accept Challenge" (sends `/accept_challenge <server_id>`). Other users can click "Join Challenge" (sends `/join_challenge <server_id>`) to be added as participants to the database record for that challenge.
4.  When the admin accepts:
    * The server updates the challenge status to "accepted".
    * It launches a new Godot game server process in headless mode (`FinalLinux.x86_64 --server --headless --ip=<server_ip> --<player_count_flag>`). The `<player_count_flag>` (e.g., `--four`) is determined by the number of participants.
    * A separate thread (`monitor_game_process`) is started to monitor the stdout of this Godot server process for a "WINNER:" message.
    * The server sends a "MINIGAME_INVITE" message to all registered participants (challenger, admin, and joiners). This message includes the game server IP (currently `DUMMY_MINIGAME_IP = "192.168.50.91"`), port, and participant usernames.
5.  Client applications (`app.py`) receiving the "MINIGAME_INVITE":
    * If the current user is one of the participants, it automatically launches the Godot game client (`FinalLinux.x86_64 --player --ip=<game_ip> --name=<username>`).
6.  Godot Game Play:
    * Players connect to the Godot server.
    * The Godot game server, upon game completion, is expected to print "WINNER: <username>" to its standard output.
7.  Winner Detection & Conclusion:
    * The `monitor_game_process` thread on the Python server reads this output, extracts the winner's username.
    * It updates the challenge status to "completed", records the winner, and updates the server's admin to be the winner in the database.
    * A system message is broadcast to the chat server announcing the winner and the new admin.

---

## 🔧 Troubleshooting

* **Connection Issues**:
    * Ensure the server is running before starting the client.
    * Verify the IP address and port in `app.py` match the server's configuration.
    * Check firewall settings on the server machine to allow incoming connections on the chosen port.
* **Godot Game Not Launching**:
    * Confirm that the `GodotGame` directory contains the correct executables (`FinalLinux.x86_64` or `FinalWindows.exe`).
    * On Linux, ensure `FinalLinux.x86_64` and `FinalLinux.sh` have execute permissions (`chmod +x <file>`).
    * The server log might show errors if it cannot find or execute the Godot server.
* **"Address already in use"**: If the server fails to start with this error, another application (or a previous instance of this server) is using the port. Stop the other application or choose a different port.
* **Database Errors**: If you encounter SQLite errors, deleting the `chat_app.db` file will allow the server to recreate it on the next run (this will erase all existing data).

---
Enjoy using Chat.io!
