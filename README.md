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

**Chat.io** is a dynamic, multi-user chat application that enables users to connect to various servers, engage in real-time messaging, and challenge the admin in exciting minigames developed with the Godot Engine to become the new leader of the group. The application features a robust client-server architecture, user authentication, and a rich graphical user interface built with PySide6.

---

![clideo_editor_23b778ab496547c296c5ade344fc6901](https://github.com/user-attachments/assets/99263c93-7f97-40c8-bb2b-74eed8925a37)

## 🌟 Features

* **User Authentication**: Secure registration and login system for users.
* **Real-Time Messaging**: Instantaneous message exchange within designated chat servers.
* **Server Management**:
    * Create new chat servers with unique invite codes.
    * Join existing servers using invite codes.
    * Leave servers.
    * List all available servers and servers the user is a member of.
* **Admin Controls**:
    * Automatic admin reassignment if the current admin leaves or loses a challenge.
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
* MongoDB
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
    The application will attempt to connect to the server IP `127.0.0.1` and port `1235` as hardcoded in `app.py`. You may need to adjust this in `app.py` if your server is running on a different IP or you used a different port.

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

Enjoy using Chat.io!
