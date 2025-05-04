import socket          
import threading
import os
import sys
import database

clients = {}
lock = threading.Lock()

class ClientThread(threading.Thread):
    def __init__(self, client_socket, addr, user):
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.running = True
        self.client_username = user

        with lock:
            clients[addr] = client_socket

    def run(self):
        print(f"[+] New thread started for {self.addr}")
        with lock:
            for addr, sock in clients.items():
                if addr != self.addr:
                    try:
                        sock.send(f"{self.client_username} joined the chat".encode())
                    except:
                        continue
        try:
            while self.running:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break
                print(f"[{self.addr}] {data}")
                if data.lower() == "close":
                    break
                with lock:
                    for addr, sock in clients.items():
                        if addr != self.addr:
                            try:
                                sock.send(data.encode())
                            except:
                                continue
        except Exception as e:
            print(f"Error with {self.addr}: {e}")
        finally:
            with lock:
                for addr, sock in clients.items():
                    if addr != self.addr:
                        try:
                            sock.send(f"{self.client_username} left the chat".encode())
                        except:
                            continue
                del clients[self.addr]
            self.client_socket.close()
            print(f"[-] Connection closed with {self.addr}")

def handle_client(client_socket, addr):
    client_socket.send("Welcome to the chat! Enter username:".encode())
    client_username = client_socket.recv(1024).decode()
    if not client_username:
        client_socket.send("closed".encode())
    else:
        t = ClientThread(client_socket, addr, client_username)
        t.start()

def init_server(port):
    try:
        s = socket.socket()
        print("Socket successfully created")
        s.bind(('0.0.0.0', port))
        print(f"socket binded to {port}")
        s.listen(5)
        print("socket is listening...")
        while True:
            client_socket, addr = s.accept()
            print(f"Accepted connection from {addr[0]}:{addr[1]}")
            thread = threading.Thread(target=handle_client, args=(client_socket, addr,))
            thread.start()
    except Exception as error:
        print(f"{error}")

if __name__ == "__main__":
    print(sys.argv[1])
    port = int(sys.argv[1])
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Initializing database")
    database.initialize_database()
    init_server(port)
