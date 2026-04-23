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
groups = {}  # group_name -> set of nicknames

def get_time():
    return datetime.now().strftime('[%I:%M %p]')

def broadcast(message):
    for client in clients:
        try:
            client.send(message)
        except:
            pass

def broadcast_userlist():
    user_list = ','.join(nicknames)
    for client in clients:
        try:
            client.send(f'USERLIST {user_list}\n'.encode('ascii'))
        except:
            pass

def broadcast_grouplist():
    """Push group list to all clients."""
    group_data = ';'.join(
        f'{name}:{",".join(members)}' for name, members in groups.items()
    )
    for client in clients:
        try:
            client.send(f'GROUPLIST {group_data}\n'.encode('ascii'))
        except:
            pass

def kick_user(name):
    if name in nicknames:
        idx = nicknames.index(name)
        c = clients[idx]
        clients.remove(c)
        nicknames.remove(name)
        try:
            c.send('KICKED\n'.encode('ascii'))
            c.close()
        except:
            pass
        broadcast_userlist()
        print(f'{name} was kicked!')

def handle(client):
    while True:
        try:
            msg = client.recv(2048).decode('ascii')
            decoded = msg.strip()
            if not decoded:
                continue

            sender_nick = nicknames[clients.index(client)]

            # KICK
            if decoded.startswith('KICK '):
                if sender_nick == 'admin':
                    kick_user(decoded[5:].strip())
                else:
                    client.send('REFUSED\n'.encode('ascii'))

            # BAN
            elif decoded.startswith('BAN '):
                if sender_nick == 'admin':
                    name_to_ban = decoded[4:].strip()
                    kick_user(name_to_ban)
                    with open('bans.txt', 'a') as f:
                        f.write(f'{name_to_ban}\n')
                    print(f'{name_to_ban} was banned!')
                else:
                    client.send('REFUSED\n'.encode('ascii'))

            # DM to specific user or ALL
            elif decoded.startswith('DM '):
                parts = decoded[3:].split(' ', 1)
                if len(parts) == 2:
                    target_nick, dm_message = parts
                    time = get_time()
                    if target_nick == 'ALL':
                        # Global broadcast to every client
                        for c in clients:
                            try:
                                c.send(f'GLOBAL|{sender_nick}|{dm_message}|{time}\n'.encode('ascii'))
                            except:
                                pass
                    elif target_nick in nicknames:
                        target_client = clients[nicknames.index(target_nick)]
                        target_client.send(f'DM|{sender_nick}|{dm_message}|{time}\n'.encode('ascii'))
                        # Echo back to sender
                        client.send(f'DM_SENT|{target_nick}|{dm_message}|{time}\n'.encode('ascii'))
                    else:
                        client.send(f'DMERR User "{target_nick}" not found.\n'.encode('ascii'))

            # Create group
            elif decoded.startswith('MKGROUP '):
                parts = decoded[8:].split(' ', 1)
                group_name = parts[0].strip()
                members_raw = parts[1].strip() if len(parts) > 1 else ''
                members = set(m.strip() for m in members_raw.split(',') if m.strip())
                members.add(sender_nick)  # creator always in group
                if group_name not in groups:
                    groups[group_name] = members
                    broadcast_grouplist()
                    # Notify members
                    for m in members:
                        if m in nicknames:
                            mc = clients[nicknames.index(m)]
                            try:
                                mc.send(f'GROUP_ADDED|{group_name}|{sender_nick}\n'.encode('ascii'))
                            except:
                                pass
                else:
                    client.send(f'GRPERR Group "{group_name}" already exists.\n'.encode('ascii'))

            # Group message
            elif decoded.startswith('GMSG '):
                parts = decoded[5:].split(' ', 1)
                if len(parts) == 2:
                    group_name, gm_message = parts
                    time = get_time()
                    if group_name in groups and sender_nick in groups[group_name]:
                        for m in groups[group_name]:
                            if m in nicknames:
                                mc = clients[nicknames.index(m)]
                                try:
                                    mc.send(f'GMSG|{group_name}|{sender_nick}|{gm_message}|{time}\n'.encode('ascii'))
                                except:
                                    pass
                    else:
                        client.send(f'GRPERR Not a member of "{group_name}".\n'.encode('ascii'))

        except:
            if client in clients:
                idx = clients.index(client)
                nick = nicknames[idx]
                clients.remove(client)
                nicknames.remove(nick)
                try:
                    client.close()
                except:
                    pass
                broadcast_userlist()
            break

def receive():
    open('bans.txt', 'a').close()
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        client.send("Nick\n".encode('ascii'))
        nickname = client.recv(1024).decode('ascii').strip()

        # Check bans
        with open('bans.txt', 'r') as f:
            bans = [b.strip() for b in f.readlines()]
        if nickname in bans:
            client.send('BAN\n'.encode('ascii'))
            client.close()
            continue

        # Prevent duplicate nicknames
        if nickname in nicknames:
            client.send('DUPE\n'.encode('ascii'))
            client.close()
            continue

        # Admin password check
        if nickname == 'admin':
            client.send('PASS\n'.encode('ascii'))
            password = client.recv(1024).decode('ascii').strip()
            if password != 'adminpass':
                client.send('REFUSE\n'.encode('ascii'))
                client.close()
                continue
            client.send('OK\n'.encode('ascii'))

        nicknames.append(nickname)
        clients.append(client)

        print(f'Nickname: {nickname}')
        client.send('Connected\n'.encode('ascii'))
        broadcast_userlist()
        # Send existing groups to new user
        broadcast_grouplist()

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

print("Server is listening...")
receive()