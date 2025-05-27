import os
import platform
import struct

def detect_os():
    """Detects the operating system and returns its name."""
    return platform.system()

def is_windows():
    """Checks if the operating system is Windows."""
    return os.name == 'nt'

def is_linux():
    """Checks if the operating system is Linux."""
    return os.name == 'posix' and detect_os() == "Linux"

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

# Debug: Print to verify
print(f"GODOT_EXECUTABLE_PATH: {GODOT_EXECUTABLE_PATH}")