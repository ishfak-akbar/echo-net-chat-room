import threading
import socket
from datetime import datetime

host = '127.0.0.1'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((host, port))
server.listen()

clients = []
nicknames = []

def get_time():
    return datetime.now().strftime('[%I:%M %p]')

def broadcast(message):
    for client in clients:
        client.send(message)

def kick_user(name):
    if name in nicknames:
        name_index = nicknames.index(name)
        client_to_kick = clients[name_index]
        clients.remove(client_to_kick)
        client_to_kick.send('You were kicked by an admin!'.encode('ascii'))
        client_to_kick.close()
        nicknames.remove(name)
        broadcast(f'{get_time()} {name} was kicked by an admin!'.encode('ascii'))
        print(f'{name} was kicked!')

def handle(client):
    while True:
        try:
            msg = client.recv(1024)
            decoded = msg.decode('ascii')

            if decoded.startswith('KICK'):
                if nicknames[clients.index(client)] == 'admin':
                    name_to_kick = decoded[5:]
                    kick_user(name_to_kick)
                else:
                    client.send('Command was refused'.encode('ascii'))

            elif decoded.startswith('BAN'):
                if nicknames[clients.index(client)] == 'admin':
                    name_to_ban = decoded[4:]
                    kick_user(name_to_ban)
                    with open('bans.txt', 'a') as f:    
                        f.write(f'{name_to_ban}\n')
                    print(f'{name_to_ban} was banned!')
                else:
                    client.send('Command was refused'.encode('ascii'))

            else:
                broadcast(msg)

        except:
            if client in clients:
                index = clients.index(client)
                clients.remove(client)
                client.close()
                nickname = nicknames[index]
                broadcast(f'{get_time()} {nickname} has left the chat'.encode('ascii'))
                nicknames.remove(nickname)
            break

def receive():
    open('bans.txt', 'a').close()

    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        client.send("Nick".encode('ascii'))
        nickname = client.recv(1024).decode('ascii')

        with open('bans.txt', 'r') as f:
            bans = f.readlines()

        if nickname+'\n' in bans:
            client.send('BAN'.encode('ascii'))
            client.close()                              
            continue

        if nickname == 'admin':
            client.send('PASS'.encode('ascii'))
            password = client.recv(1024).decode('ascii')
            if password != 'adminpass':
                client.send('REFUSE'.encode('ascii'))
                client.close()
                continue

        nicknames.append(nickname)
        clients.append(client)

        print(f'Nickname of the client is {nickname}!')
        client.send('Connected to the server!'.encode('ascii'))
        broadcast(f'{get_time()} {nickname} joined the chat!'.encode('ascii'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

print("Server is listening...")
receive()