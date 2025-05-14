import socket

def connectToServer(port):
    sock = socket.socket()

    try:
        sock.connect(('127.0.0.1', port))

    except Exception as e:
        print("Connection error...")
        return 0

    return sock

def receiveMessage(sock):
    return sock.recv(1024).decode()