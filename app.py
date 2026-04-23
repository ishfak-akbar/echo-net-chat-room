import socket
import threading
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'tcpchatroom_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

tcp_clients = {}
nick_map    = {}  

def get_tcp(sid):
    return tcp_clients.get(sid)

def listen_to_server(sid, tcp_client):
    buffer = ''
    while True:
        try:
            data = tcp_client.recv(1024).decode('ascii')
            buffer += data

            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                if line.startswith('USERLIST'):
                    users = [u for u in line[9:].split(',') if u]
                    socketio.emit('userlist', {'users': users}, to=sid)

                elif line == 'KICKED':
                    socketio.emit('kicked', {}, to=sid)
                    tcp_clients.pop(sid, None)
                    nick_map.pop(sid, None)
                    return

                elif line.startswith('DM|'):
                    parts = line[3:].split('|', 1)
                    if len(parts) == 2:
                        sender, msg = parts
                        from datetime import datetime
                        time = datetime.now().strftime('[%I:%M %p]')
                        socketio.emit('dm', {'sender': sender, 'msg': msg, 'time': time}, to=sid)

                elif line.startswith('DMERR'):
                    socketio.emit('dmerr', {'msg': line[6:]}, to=sid)

        except:
            socketio.emit('server_error', {}, to=sid)
            break

    tcp_clients.pop(sid, None)
    nick_map.pop(sid, None)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nick     = request.form.get('nickname', '').strip()
        password = request.form.get('password', '').strip() or None

        if not nick:
            return render_template('login.html', error='Please enter a nickname.')

        session['nickname'] = nick
        session['password'] = password
        return redirect(url_for('admin') if nick == 'admin' else url_for('chat'))

    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'nickname' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', nickname=session['nickname'])

@app.route('/admin')
def admin():
    if session.get('nickname') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin.html')


@socketio.on('connect')
def on_connect():
    sid      = request.sid
    nick     = session.get('nickname')
    password = session.get('password')

    if not nick:
        return

    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.connect(('127.0.0.1', 55555))

        msg = tcp.recv(1024).decode('ascii')
        if msg == 'Nick':
            tcp.send(nick.encode('ascii'))

        response = tcp.recv(1024).decode('ascii')

        if response == 'BAN':
            emit('banned', {})
            tcp.close()
            return

        if response == 'PASS':
            if not password:
                emit('auth_error', {})
                tcp.close()
                return
            tcp.send(password.encode('ascii'))
            auth = tcp.recv(1024).decode('ascii')
            if auth == 'REFUSE':
                emit('auth_error', {})
                tcp.close()
                return
            tcp.recv(1024) 

        tcp_clients[sid] = tcp
        nick_map[sid]    = nick

        t = threading.Thread(target=listen_to_server, args=(sid, tcp), daemon=True)
        t.start()

        emit('connected', {'nick': nick})

    except Exception as e:
        emit('server_error', {'msg': str(e)})

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    tcp = tcp_clients.pop(sid, None)
    nick_map.pop(sid, None)
    if tcp:
        try:
            tcp.close()
        except:
            pass

@socketio.on('send_dm')
def handle_dm(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    msg    = data.get('msg', '').strip()
    if target and msg and tcp:
        tcp.send(f'DM {target} {msg}\n'.encode('ascii'))

@socketio.on('kick_user')
def handle_kick(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'KICK {target}\n'.encode('ascii'))

@socketio.on('ban_user')
def handle_ban(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'BAN {target}\n'.encode('ascii'))

@socketio.on('broadcast_msg')
def handle_broadcast(data):
    sid = request.sid
    tcp = get_tcp(sid)
    msg = data.get('msg', '').strip()
    if msg and tcp:
        from datetime import datetime
        time = datetime.now().strftime('[%I:%M %p]')
        tcp.send(f'DM ALL {time} 📢 ADMIN: {msg}\n'.encode('ascii'))

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)