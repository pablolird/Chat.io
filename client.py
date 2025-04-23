import socket
import os
import threading
import sys

running = True

def sendingThread(socket):
    global running
    while running:
        message = input()
        if message == "close":
            print("Disconnecting")
            running = False
            socket.send(message.encode())
        else:
            message = f"{user}: {message}"
            socket.send(message.encode())

def receivingThread(socket):
    global running
    while running:
        try:
            response = socket.recv(1024).decode()
            if response.lower() == "closed":
                print("Server closed successfully")
                break
            else:
                print(response)
        except:
            break


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    s = socket.socket()
    port = int(sys.argv[1])

    s.connect(('127.0.0.1', port))
    print(s.recv(1024).decode())

    user = input()
    s.send(user.encode())

    os.system('cls' if os.name == 'nt' else 'clear')

    sending_Thread = threading.Thread(target=sendingThread, args=(s,))
    receiving_Thread = threading.Thread(target=receivingThread, args=(s,))

    sending_Thread.start()
    receiving_Thread.start()

    sending_Thread.join()
    receiving_Thread.join()

    s.close()
