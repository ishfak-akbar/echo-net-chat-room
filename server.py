import threading
import socket
 
host = '127.0.0.1'
port = 55555
 
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((host, port))
server.listen()
 
clients = []
nicknames = []
 
def broadcast(message):
    for client in clients:
        client.send(message)
 
def handle(client):
    while True:
        try:
            message = client.recv(1024)
            broadcast(message)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'{nickname} has left the chat'.encode('ascii'))
            nicknames.remove(nickname)
            break
 
def receive():
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")
 
        client.send("Nick".encode('ascii'))
        nickname = client.recv(1024).decode('ascii')
        nicknames.append(nickname)
        clients.append(client)
 
        print(f'Nickname of the client is {nickname}!')
        client.send('Connected to the server!'.encode('ascii'))
        broadcast(f'{nickname} joined the chat!'.encode('ascii'))
 
        thread = threading.Thread(target=handle, args=(client,))
        thread.start()
 
print("Server is listening...")
receive()