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
    """Background thread per user — forwards TCP messages to that browser tab."""
    while True:
        try:
            message = tcp_client.recv(1024).decode('ascii')
            if message.startswith('USERLIST'):
                users = [u for u in message[9:].split(',') if u]
                socketio.emit('userlist', {'users': users}, to=sid)
            elif message == 'KICKED':
                socketio.emit('kicked', {}, to=sid)
                break
            else:
                if '[DM ' in message:
                    socketio.emit('message', {'msg': message}, to=sid)
                else:
                    socketio.emit('message', {'msg': message}, to=sid)
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
                emit('auth_error', {'msg': 'Password required for admin.'})
                tcp.close()
                return
            tcp.send(password.encode('ascii'))
            auth = tcp.recv(1024).decode('ascii')
            if auth == 'REFUSE':
                emit('auth_error', {'msg': 'Wrong admin password.'})
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


@socketio.on('send_message')
def handle_message(data):
    sid = request.sid
    tcp = get_tcp(sid)
    msg = data.get('msg', '').strip()
    if msg and tcp:
        from datetime import datetime
        time = datetime.now().strftime('[%I:%M %p]')
        nick = nick_map.get(sid, '')
        tcp.send(f'{time} {nick}: {msg}'.encode('ascii'))

@socketio.on('send_dm')
def handle_dm(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    msg    = data.get('msg', '').strip()
    if target and msg and tcp:
        tcp.send(f'DM {target} {msg}'.encode('ascii'))

@socketio.on('kick_user')
def handle_kick(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'KICK {target}'.encode('ascii'))

@socketio.on('ban_user')
def handle_ban(data):
    sid    = request.sid
    tcp    = get_tcp(sid)
    target = data.get('target', '')
    if target and tcp:
        tcp.send(f'BAN {target}'.encode('ascii'))

@socketio.on('get_users')
def handle_get_users():
    sid = request.sid
    tcp = get_tcp(sid)
    if tcp:
        tcp.send('USERLIST'.encode('ascii'))

@socketio.on('broadcast_msg')
def handle_broadcast(data):
    sid = request.sid
    tcp = get_tcp(sid)
    msg = data.get('msg', '').strip()
    if msg and tcp:
        from datetime import datetime
        time = datetime.now().strftime('[%I:%M %p]')
        tcp.send(f'{time} 📢 ADMIN: {msg}'.encode('ascii'))

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)