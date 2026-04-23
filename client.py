import socket
import threading
from datetime import datetime

nickname = input("Choose a nickname: ")
password = None                         
if nickname == 'admin':
    password = input("Enter a password: ")

stop_thread = False                      

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 55555))

def get_time():
    return datetime.now().strftime('[%I:%M %p]')

def receive():
    global stop_thread
    while True:
        if stop_thread:
            break
        try:
            message = client.recv(1024).decode('ascii')
            if message == "Nick":
                client.send(nickname.encode('ascii'))
                next_message = client.recv(1024).decode('ascii')
                if next_message == 'PASS':
                    client.send(password.encode('ascii'))
                    if client.recv(1024).decode('ascii') == "REFUSE":
                        print("Wrong Password")
                        stop_thread = True
                elif next_message == "BAN":
                    print('Connection was refused because of ban!')
                    client.close()
                    stop_thread = True
            else:
                print(message)
        except:
            print("Error occurred!")
            client.close()
            break

def write():
    global stop_thread
    while True:
        if stop_thread:
            break
        text = input("")
        cmd = text.strip()
        if cmd.startswith('/'):
            if nickname == 'admin':
                if cmd.startswith('/kick'):
                    client.send(f'KICK {cmd[6:]}'.encode('ascii'))   
                elif cmd.startswith('/ban'):
                    client.send(f'BAN {cmd[5:]}'.encode('ascii')) 
            elif cmd.startswith('/dm'):
                parts = cmd[4:].split(' ', 1)                                       
                if len(parts) == 2:
                    target_nick, dm_message = parts
                    client.send(f'DM {target_nick} {dm_message}'.encode('ascii'))
                else:
                    print('Usage: /dm <nickname> <message>')
            else:
                print('Command can only be accessed by admin')
        else:
            message = f'{get_time()} {nickname}: {text}'
            client.send(message.encode('ascii'))                    

receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()