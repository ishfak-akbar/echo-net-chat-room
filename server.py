import threading
import socket
from datetime import datetime
import database as db

try:
    db.init_db()
except Exception as e:
    print(f"[FATAL] Could not initialize database: {e}")
    exit(1)

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
    # Get groups from database
    groups_data = {}
    for nick in nicknames:
        user_groups = db.get_user_groups(nick)
        for group_name, members in user_groups.items():
            if group_name not in groups_data:
                groups_data[group_name] = set(members)
            else:
                groups_data[group_name].update(members)
    
    group_data = ';'.join(
        f'{name}:{",".join(members)}' for name, members in groups_data.items()
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
        db.set_offline(name)
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
                    db.add_banned_user(name_to_ban)
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
                        db.save_global(sender_nick, dm_message)
                    if target_nick in nicknames:
                        target_client = clients[nicknames.index(target_nick)]
                        target_client.send(f'DM|{sender_nick}|{dm_message}|{time}\n'.encode('ascii'))
                    db.save_dm(sender_nick, target_nick, dm_message)
                    client.send(f'DM_SENT|{target_nick}|{dm_message}|{time}\n'.encode('ascii'))

            # Create group
            elif decoded.startswith('MKGROUP '):
                parts = decoded[8:].split(' ', 1)
                group_name = parts[0].strip()
                members_raw = parts[1].strip() if len(parts) > 1 else ''
                members = set(m.strip() for m in members_raw.split(',') if m.strip())
                members.add(sender_nick)  # creator always in group
                
                # Check if group exists in database
                existing_groups = db.get_user_groups(sender_nick)
                if group_name not in existing_groups:
                    db.save_group(group_name, list(members))
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
                    user_groups = db.get_user_groups(sender_nick)
                    if group_name in user_groups and sender_nick in user_groups[group_name]:
                        db.save_group_message(group_name, sender_nick, gm_message)
                        for m in user_groups[group_name]:
                            if m in nicknames:
                                mc = clients[nicknames.index(m)]
                                try:
                                    mc.send(f'GMSG|{group_name}|{sender_nick}|{gm_message}|{time}\n'.encode('ascii'))
                                except:
                                    pass
                    else:
                        client.send(f'GRPERR Not a member of "{group_name}".\n'.encode('ascii'))
            
            elif decoded.startswith('UNBAN'):
                if nicknames[clients.index(client)] == 'admin':
                    name_to_unban = decoded[6:].strip()
                    db.remove_banned_user(name_to_unban)
                    client.send(f'UNBAN_OK {name_to_unban}\n'.encode('ascii'))
                    print(f'{name_to_unban} was unbanned!')
                else:
                    client.send('REFUSED\n'.encode('ascii'))
                    
            elif decoded == 'BANLIST':
                if nicknames[clients.index(client)] == 'admin':
                    bans = db.get_banned_users()
                    ban_list = ','.join(bans) if bans else ''
                    client.send(f'BANLIST {ban_list}\n'.encode('ascii'))
                        
            elif decoded == 'USERLIST':
                user_list = ','.join(nicknames)
                client.send(f'USERLIST {user_list}\n'.encode('ascii'))

        except Exception as e:
            print(f"Error handling client: {e}")
            if client in clients:
                idx = clients.index(client)
                nick = nicknames[idx]
                db.set_offline(nick)
                clients.remove(client)
                nicknames.remove(nick)
                try:
                    client.close()
                except:
                    pass
                broadcast_userlist()
            break

def receive():
    while True:
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        client.send("Nick\n".encode('ascii'))
        nickname = client.recv(1024).decode('ascii').strip()

        # Check bans from database
        if db.is_banned(nickname):
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
            
        if nickname in nicknames:
            client.send('NICK_TAKEN\n'.encode('ascii'))
            client.close()
            continue

        nicknames.append(nickname)
        clients.append(client)
        
        db.add_user(nickname)
        db.set_online(nickname)

        print(f'Nickname: {nickname}')
        client.send('Connected\n'.encode('ascii'))
        broadcast_userlist()
        # Send existing groups to new user
        broadcast_grouplist()

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

print("Server is listening...")
receive()