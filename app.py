import socket
import threading
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
import database as db
from datetime import datetime
from flask_socketio import disconnect
import uuid

app = Flask(__name__)
app.secret_key = 'tcpchatroom_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'dp')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MSG_IMG_FOLDER = os.path.join('static', 'uploads', 'msg_images')
os.makedirs(MSG_IMG_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  

socketio = SocketIO(app, cors_allowed_origins="*")

tcp_clients = {}
nick_map = {}
nick_to_sid = {}

def get_tcp(sid):
    return tcp_clients.get(sid)

def broadcast_user_lists():
    """Broadcast updated all_users and online_users to every connected client."""
    all_users    = db.get_all_users()
    online_users = list(nick_to_sid.keys())
    for s in nick_to_sid.values():
        socketio.emit('all_users',    {'users': all_users},    to=s)
        socketio.emit('online_users', {'users': online_users}, to=s)

def listen_to_server(sid, tcp_client):
    buffer = ''
    while True:
        try:
            data = tcp_client.recv(2048).decode('ascii')
            if not data:
                break
            buffer += data

            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                if line.startswith('USERLIST '):
                    # Ignored — user lists are managed by app.py directly
                    pass

                elif line == 'KICKED':
                    socketio.emit('kicked', {}, to=sid)
                    tcp_clients.pop(sid, None)
                    nick_map.pop(sid, None)
                    return

                elif line == 'BAN':
                    socketio.emit('banned', {}, to=sid)
                    tcp_clients.pop(sid, None)
                    nick_map.pop(sid, None)
                    return

                elif line.startswith('BANLIST'):
                    bans = [b for b in line[8:].split(',') if b]
                    socketio.emit('banlist', {'bans': bans}, to=sid)

                elif line.startswith('UNBAN_OK'):
                    name = line[9:].strip()
                    socketio.emit('unban_ok', {'name': name}, to=sid)

                elif line == 'NICK_TAKEN':
                    socketio.emit('nick_taken', {}, to=sid)
                    return

                elif line.startswith('DM|'):
                    parts = line[3:].split('|', 2)
                    if len(parts) == 3:
                        sender, msg, time = parts
                        socketio.emit('dm', {'sender': sender, 'msg': msg, 'time': time}, to=sid)
                
                elif line.startswith('READ_RECEIPT|'):
                    sender = line.split('|')[1]
                    socketio.emit('read_receipt', {'sender': sender}, to=sid)

                elif line.startswith('DM_SENT|'):
                    parts = line[8:].split('|', 2)
                    if len(parts) == 3:
                        target, msg, time = parts
                        socketio.emit('dm_sent', {'target': target, 'msg': msg, 'time': time}, to=sid)

                elif line.startswith('GLOBAL|'):
                    parts = line[7:].split('|', 2)
                    if len(parts) == 3:
                        sender, msg, time = parts
                        socketio.emit('global_msg', {'sender': sender, 'msg': msg, 'time': time}, to=sid)

                elif line.startswith('DMERR '):
                    socketio.emit('dmerr', {'msg': line[6:]}, to=sid)

                elif line.startswith('GROUPLIST '):
                    raw = line[10:]
                    groups = {}
                    if raw:
                        for entry in raw.split(';'):
                            if ':' in entry:
                                gname, members_raw = entry.split(':', 1)
                                groups[gname] = members_raw.split(',')
                    socketio.emit('grouplist', {'groups': groups}, to=sid)

                elif line.startswith('GROUP_ADDED|'):
                    parts = line[12:].split('|', 1)
                    if len(parts) == 2:
                        gname, creator = parts
                        socketio.emit('group_added', {'group': gname, 'creator': creator}, to=sid)

                elif line.startswith('GMSG|'):
                    parts = line[5:].split('|', 3)
                    if len(parts) == 4:
                        gname, sender, msg, time = parts
                        socketio.emit('gmsg', {'group': gname, 'sender': sender, 'msg': msg, 'time': time}, to=sid)

                elif line.startswith('GRPERR '):
                    socketio.emit('grperr', {'msg': line[7:]}, to=sid)

        except:
            break

    socketio.emit('server_error', {}, to=sid)
    tcp_clients.pop(sid, None)
    nick_map.pop(sid, None)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nick     = request.form.get('nickname', '').strip()
        password = request.form.get('password', '').strip() or None

        if not nick:
            return render_template('login.html', error='Please enter a nickname.')

        if nick == 'admin':
            if not password:
                return render_template('login.html', error='Admin password is required.')
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(3)
                test_sock.connect(('127.0.0.1', 55555))
                test_sock.recv(1024)
                test_sock.send((nick + '\n').encode('ascii'))
                resp = test_sock.recv(1024).decode('ascii').strip()
                if resp == 'DUPE':
                    test_sock.close()
                    return render_template('login.html', error='Username already taken.')
                if resp == 'BAN':
                    test_sock.close()
                    return render_template('login.html', error='You are banned.')
                if resp == 'PASS':
                    test_sock.send((password + '\n').encode('ascii'))
                    auth = test_sock.recv(1024).decode('ascii').strip()
                    if auth != 'OK':
                        test_sock.close()
                        return render_template('login.html', error='Wrong admin password.')
                test_sock.close()
            except Exception as e:
                return render_template('login.html', error=f'Cannot connect to server: {e}')

        session['nickname'] = nick
        session['password'] = password
        return redirect(url_for('admin') if nick == 'admin' else url_for('chat'))

    return render_template('login.html')


@app.route('/chat')
def chat():
    if 'nickname' not in session:
        return redirect(url_for('login'))
    if session.get('nickname') == 'admin':
        return redirect(url_for('admin'))
    return render_template('chat.html', nickname=session['nickname'])


@app.route('/admin')
def admin():
    if session.get('nickname') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/upload_dp', methods=['POST'])
def upload_dp():
    if 'nickname' not in session:
        return {'error': 'not logged in'}, 401
    file = request.files.get('dp')
    if not file:
        return {'error': 'no file'}, 400
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return {'error': 'invalid type'}, 400
    filename = secure_filename(f"{session['nickname']}.{ext}")
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return {'url': url_for('static', filename=f'dp/{filename}')}, 200

@app.route('/get_dp/<nickname>')
def get_dp(nickname):
    for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        path = os.path.join(UPLOAD_FOLDER, f'{nickname}.{ext}')
        if os.path.exists(path):
            return {'url': url_for('static', filename=f'dp/{nickname}.{ext}')}, 200
    return {'url': None}, 200

@app.route('/upload_msg_img', methods=['POST'])
def upload_msg_img():
    if 'nickname' not in session:
        return {'error': 'not logged in'}, 401
    file = request.files.get('img')
    if not file:
        return {'error': 'no file'}, 400
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return {'error': 'invalid type'}, 400
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(MSG_IMG_FOLDER, filename))
    return {'url': url_for('static', filename=f'uploads/msg_images/{filename}')}, 200

@socketio.on('connect')
def on_connect():
    sid      = request.sid
    nick     = session.get('nickname')
    password = session.get('password')

    if not nick:
        return

    # Clean up any existing session for this nick cleanly
    existing_sid = nick_to_sid.get(nick)
    if existing_sid:
        old_tcp = tcp_clients.pop(existing_sid, None)
        if old_tcp:
            try:
                old_tcp.close()
            except:
                pass
        nick_map.pop(existing_sid, None)
        nick_to_sid.pop(nick, None)

    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.connect(('127.0.0.1', 55555))

        msg = tcp.recv(1024).decode('ascii').strip()
        if msg == 'Nick':
            tcp.send((nick + '\n').encode('ascii'))

        response = tcp.recv(1024).decode('ascii').strip()

        if response == 'BAN':
            emit('banned', {})
            tcp.close()
            return

        if response == 'DUPE':
            emit('nick_taken', {})
            tcp.close()
            return

        if response == 'NICK_TAKEN':
            emit('nick_taken', {})
            tcp.close()
            return

        if response == 'PASS':
            if not password:
                emit('auth_error', {})
                tcp.close()
                return
            tcp.send(password.encode('ascii'))
            auth = tcp.recv(1024).decode('ascii').strip()
            if auth == 'REFUSE':
                emit('auth_error', {})
                tcp.close()
                return
            tcp.recv(1024)  # consume 'Connected'

        tcp_clients[sid]  = tcp
        nick_map[sid]     = nick
        nick_to_sid[nick] = sid
        db.add_user(nick)

        try:
            db.set_online(nick)
        except Exception as e:
            print(f"[WARN] Could not set online status for {nick}: {e}")

        # Send global history
        global_history = db.get_global_history()
        emit('load_global', {'msgs': global_history}, to=sid)

        try:
            all_senders = db.get_dm_senders(nick)
            for sender in all_senders:
                history = db.get_dm_history(nick, sender)
                if history:
                    socketio.emit('offline_dm_history', {
                        'sender': sender,
                        'msgs': history
                    }, to=sid)
        except Exception as e:
            print(f"[WARN] Could not load offline messages for {nick}: {e}")

        # Start listener thread
        t = threading.Thread(target=listen_to_server, args=(sid, tcp), daemon=True)
        t.start()

        emit('connected', {'nick': nick})
        broadcast_user_lists()
        broadcasts = db.get_broadcasts()
        emit('load_broadcasts', {'msgs': broadcasts}, to=sid)

    except Exception as e:
        print(f"[on_connect ERROR] {e}")
        emit('server_error', {'msg': str(e)})


@socketio.on('disconnect')
def on_disconnect():
    sid  = request.sid
    nick = nick_map.get(sid)
    tcp  = tcp_clients.pop(sid, None)
    nick_map.pop(sid, None)

    # Remove from online map before broadcasting
    if nick and nick_to_sid.get(nick) == sid:
        nick_to_sid.pop(nick, None)

    if tcp:
        try:
            tcp.close()
        except:
            pass

    if nick:
        try:
            db.set_offline(nick)
        except Exception as e:
            print(f"[WARN] Could not set offline for {nick}: {e}")

        broadcast_user_lists()


@socketio.on('get_users')
def send_users():
    sid = request.sid
    all_users = db.get_all_users()
    online_users = list(nick_to_sid.keys())
    socketio.emit('all_users', {'users': all_users}, to=sid)
    socketio.emit('online_users', {'users': online_users}, to=sid)


@socketio.on('send_dm')
def handle_dm(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    msg    = data.get('msg', '').strip()
    image_url = data.get('image_url')

    if not target:
        return

    time = datetime.now().strftime('[%I:%M %p]')

    if image_url:
        sender = nick_map.get(sid)
        db.save_dm_image(sender, target, image_url, msg)
        target_sid = nick_to_sid.get(target)
        if target_sid:
            socketio.emit('dm', {'sender': sender, 'msg': msg, 'image_url': image_url, 'time': time}, to=target_sid)
        socketio.emit('dm_sent', {'target': target, 'msg': msg, 'image_url': image_url, 'time': time}, to=sid)
    else:
        if msg and tcp:
            tcp.send(f'DM {target} {msg}\n'.encode('ascii'))
        
@socketio.on('mark_read')
def handle_mark_read(data):
    sid = request.sid
    tcp = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'MARK_READ {target}\n'.encode('ascii'))

@socketio.on('get_unread')
def handle_get_unread():
    sid = request.sid
    nick = nick_map.get(sid)
    if nick:
        unread = db.get_unread_count(nick)
        emit('unread_counts', {'counts': unread}, to=sid)


@socketio.on('send_global')
def handle_global(data):
    sid = request.sid
    tcp = get_tcp(sid)
    msg = data.get('msg', '').strip()
    if msg and tcp:
        tcp.send(f'DM ALL {msg}\n'.encode('ascii'))


@socketio.on('load_chat')
def load_chat(data):
    sid    = request.sid
    user   = nick_map.get(sid)
    target = data.get('target')
    if user and target:
        history = db.get_dm_history(user, target)
        socketio.emit('chat_history', {'msgs': history}, to=sid)
        db.mark_dm_as_read(user, target)
        if target in nick_to_sid:
            socketio.emit('read_receipt', {'sender': user}, to=nick_to_sid[target])


@socketio.on('load_group_history')
def load_group_history(data):
    sid        = request.sid
    group_name = data.get('group')
    if group_name:
        history = db.get_group_history(group_name)
        socketio.emit('group_history', {'msgs': history}, to=sid)


@socketio.on('request_userlist')
def send_userlist():
    sid = request.sid
    emit('userlist', {'users': list(nick_to_sid.keys())}, to=sid)


@socketio.on('kick_user')
def handle_kick(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'KICK {target}\n'.encode('ascii'))

        from datetime import datetime
        time = datetime.now().strftime('%I:%M %p')
        db.save_broadcast(f'⚠️ {target} was kicked by Admin', time)
        socketio.emit('broadcast_notice', {'msg': f'⚠️ {target} was kicked by Admin', 'time': time})

        target_sid = nick_to_sid.get(target)
        if target_sid:
            db.set_offline(target)
            old_tcp = tcp_clients.pop(target_sid, None)
            if old_tcp:
                try:
                    old_tcp.close()
                except:
                    pass
            nick_map.pop(target_sid, None)
            nick_to_sid.pop(target, None)
            socketio.emit('kicked', {}, to=target_sid)
            disconnect(sid=target_sid)
            broadcast_user_lists()


@socketio.on('ban_user')
def handle_ban(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'BAN {target}\n'.encode('ascii'))
        
        db.add_banned_user(target)
        db.set_offline(target)

        bans = db.get_banned_users()
        socketio.emit('banlist', {'bans': bans}, to=sid)

        from datetime import datetime
        time = datetime.now().strftime('%I:%M %p')
        db.save_broadcast(f'⛔ {target} was permanently banned by Admin', time)
        socketio.emit('broadcast_notice', {'msg': f'⛔ {target} was permanently banned by Admin', 'time': time})

        target_sid = nick_to_sid.get(target)
        if target_sid:
            old_tcp = tcp_clients.pop(target_sid, None)
            if old_tcp:
                try:
                    old_tcp.close()
                except:
                    pass
            nick_map.pop(target_sid, None)
            nick_to_sid.pop(target, None)
            socketio.emit('banned', {}, to=target_sid)
            disconnect(sid=target_sid)
            broadcast_user_lists()

@socketio.on('broadcast_msg')
def handle_broadcast(data):
    sid = request.sid
    msg = data.get('msg', '').strip()
    if msg:
        from datetime import datetime
        time = datetime.now().strftime('%I:%M %p')
        db.save_broadcast(msg, time)
        socketio.emit('broadcast_notice', {'msg': msg, 'time': time})
        socketio.emit('broadcast_count', {
            'count': len(db.get_broadcasts())
        })

@socketio.on("get_broadcast_count")
def handle_broadcast_count():
    emit("broadcast_count", {
        "count": len(db.get_broadcasts())
    }, to=request.sid)

@socketio.on('create_group')
def handle_create_group(data):
    sid        = request.sid
    tcp        = get_tcp(sid)
    group_name = data.get('name', '').strip()
    members    = data.get('members', [])
    if group_name and tcp:
        members_str = ','.join(members)
        tcp.send(f'MKGROUP {group_name} {members_str}\n'.encode('ascii'))


@socketio.on('send_gmsg')
def handle_gmsg(data):
    sid        = request.sid
    tcp        = get_tcp(sid)
    group_name = data.get('group', '')
    msg        = data.get('msg', '').strip()
    image_url  = data.get('image_url')

    if not group_name:
        return

    time   = datetime.now().strftime('[%I:%M %p]')
    sender = nick_map.get(sid)

    if image_url:
        db.save_group_image(group_name, sender, image_url, msg)
        members = db.get_user_groups(sender).get(group_name, [])
        for member in members:
            member_sid = nick_to_sid.get(member)
            if member_sid:
                socketio.emit('gmsg', {
                    'group': group_name, 'sender': sender,
                    'msg': msg, 'image_url': image_url, 'time': time
                }, to=member_sid)
    else:
        if msg and tcp:
            tcp.send(f'GMSG {group_name} {msg}\n'.encode('ascii'))

@socketio.on('unban_user')
def handle_unban(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'UNBAN {target}\n'.encode('ascii'))
        db.remove_banned_user(target)
        bans = db.get_banned_users()
        emit('banlist', {'bans': bans}, to=sid)
        emit('unban_ok', {'name': target}, to=sid)

        from datetime import datetime
        time = datetime.now().strftime('%I:%M %p')
        db.save_broadcast(f'✅ {target} was unbanned by Admin', time)
        socketio.emit('broadcast_notice', {'msg': f'✅ {target} was unbanned by Admin', 'time': time})


@socketio.on('get_bans')
def handle_get_bans():
    sid = request.sid
    bans = db.get_banned_users()
    emit('banlist', {'bans': bans}, to=sid)

@socketio.on('get_group_unread')
def handle_group_unread():
    sid = request.sid
    nick = nick_map.get(sid)
    if nick:
        counts = db.get_group_unread_count(nick)
        emit('group_unread_counts', {'counts': counts}, to=sid)

@socketio.on('mark_group_read')
def handle_mark_group_read(data):
    sid = request.sid
    nick = nick_map.get(sid)
    group = data.get('group')
    if nick and group:
        db.mark_group_read(nick, group)

@socketio.on('get_shared_media')
def handle_get_shared_media(data):
    sid = request.sid
    me = nick_map.get(sid)
    target = data.get('target')
    group = data.get('group')
    if group:
        media = db.get_shared_media(group_name=group)
    elif target:
        media = db.get_shared_media(me, target)
    else:
        return
    emit('shared_media', {'media': [list(r) for r in media]}, to=sid)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)