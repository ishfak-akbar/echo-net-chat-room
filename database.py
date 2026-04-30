import sqlite3
from datetime import datetime
import threading

DB_NAME = "echonet.db"

_local = threading.local()

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        nickname TEXT PRIMARY KEY
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS online_users (
        nickname TEXT PRIMARY KEY
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        type TEXT,
        time TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS groups_table (
        group_name TEXT,
        member TEXT,
        PRIMARY KEY (group_name, member)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS group_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        sender TEXT,
        message TEXT,
        time TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS global_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        message TEXT,
        time TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS banned_users (
        nickname TEXT PRIMARY KEY,
        banned_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS group_read (
        nickname TEXT,
        group_name TEXT,
        last_read_id INTEGER DEFAULT 0,
        PRIMARY KEY (nickname, group_name)
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        time TEXT
    )""")

    try:
        c.execute("ALTER TABLE messages ADD COLUMN read INTEGER DEFAULT 0")
    except:
        pass
    
    try:
        c.execute("ALTER TABLE messages ADD COLUMN read_at TEXT")
    except:
        pass

    conn.commit()
    conn.close()

def now():
    return datetime.now().strftime("[%I:%M %p]")

# USERS
def add_user(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users VALUES (?)", (nick,))
    conn.commit()
    conn.close()

def set_online(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO online_users VALUES (?)", (nick,))
    conn.commit()
    conn.close()

def set_offline(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM online_users WHERE nickname=?", (nick,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT nickname FROM users")
    return [r[0] for r in c.fetchall()]

def get_online_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT nickname FROM online_users")
    return [r[0] for r in c.fetchall()]

# Banned Users
def add_banned_user(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO banned_users VALUES (?, ?)", (nick, now()))
    conn.commit()
    conn.close()

def remove_banned_user(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE nickname=?", (nick,))
    conn.commit()
    conn.close()

def get_banned_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT nickname FROM banned_users")
    return [r[0] for r in c.fetchall()]

def is_banned(nick):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM banned_users WHERE nickname=?", (nick,))
        result = c.fetchone()
    return result is not None

# Groups
def save_group(group_name, members):
    conn = get_conn()
    c = conn.cursor()
    for member in members:
        c.execute("INSERT OR IGNORE INTO groups_table VALUES (?, ?)", (group_name, member))
    conn.commit()
    conn.close()

def get_user_groups(nick):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT group_name FROM groups_table WHERE member=?", (nick,))
    groups = {}
    for (group_name,) in c.fetchall():
        c2 = conn.cursor()
        c2.execute("SELECT member FROM groups_table WHERE group_name=?", (group_name,))
        members = [m[0] for m in c2.fetchall()]
        groups[group_name] = members
    conn.close()
    return groups

def delete_group(group_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM groups_table WHERE group_name=?", (group_name,))
    conn.commit()
    conn.close()

def save_group_message(group_name, sender, message):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO group_messages (group_name, sender, message, time) VALUES (?, ?, ?, ?)",
              (group_name, sender, message, now()))
    conn.commit()
    conn.close()

def get_group_history(group_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT sender, message, time FROM group_messages WHERE group_name=? ORDER BY id ASC", (group_name,))
    result = c.fetchall()
    conn.close()
    return result

# MESSAGES
def save_dm(sender, receiver, msg):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO messages(sender, receiver, message, type, time, read) 
                 VALUES (?, ?, ?, 'dm', ?, 0)""",
              (sender, receiver, msg, now()))
    conn.commit()
    conn.close()

def save_global(sender, msg):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO global_messages(sender, message, time)
                 VALUES (?, ?, ?)""",
              (sender, msg, now()))
    conn.commit()
    conn.close()

def get_dm_history(user1, user2):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT sender, receiver, message, time, read 
                 FROM messages 
                 WHERE (sender=? AND receiver=?)
                 OR (sender=? AND receiver=?)
                 ORDER BY id ASC""",
              (user1, user2, user2, user1))
    result = c.fetchall()
    conn.close()
    return result

def get_global_history():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT sender, message, time FROM global_messages ORDER BY id ASC")
    result = c.fetchall()
    conn.close()
    return result

def get_dm_senders(nick):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT sender FROM messages
            WHERE receiver=? AND sender!=?
            UNION
            SELECT DISTINCT receiver FROM messages
            WHERE sender=? AND receiver!=?
        """, (nick, nick, nick, nick))
        return [r[0] for r in c.fetchall()]

def mark_dm_as_read(user, sender):
    """Mark all messages from sender to user as read"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""UPDATE messages 
                 SET read = 1, read_at = ? 
                 WHERE receiver = ? AND sender = ? AND read = 0""",
              (now(), user, sender))
    conn.commit()
    conn.close()

def get_unread_count(user):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT sender, COUNT(*) as unread 
                 FROM messages 
                 WHERE receiver = ? AND read = 0 
                 GROUP BY sender""",
              (user,))
    result = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return result

def get_recent_messages(nickname):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT 
            CASE WHEN sender = ? THEN receiver ELSE sender END as other,
            message, time
        FROM messages
        WHERE (sender = ? OR receiver = ?)
        AND id IN (
            SELECT MAX(id) FROM messages
            WHERE sender = ? OR receiver = ?
            GROUP BY CASE WHEN sender = ? THEN receiver ELSE sender END
        )
    ''', (nickname, nickname, nickname, nickname, nickname, nickname))
    rows = c.fetchall()
    conn.close()
    return rows

def get_group_unread_count(nickname):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        SELECT group_name, COUNT(*) FROM group_messages
        WHERE sender != ?
        AND id > COALESCE((
            SELECT last_read_id FROM group_read
            WHERE nickname = ? AND group_name = group_messages.group_name
        ), 0)
        GROUP BY group_name
    ''', (nickname, nickname))
    result = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return result

def mark_group_read(nickname, group_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT MAX(id) FROM group_messages WHERE group_name = ?', (group_name,))
    last_id = c.fetchone()[0] or 0
    c.execute('''
        INSERT INTO group_read (nickname, group_name, last_read_id)
        VALUES (?, ?, ?)
        ON CONFLICT(nickname, group_name) DO UPDATE SET last_read_id = ?
    ''', (nickname, group_name, last_id, last_id))
    conn.commit()
    conn.close()
    
def save_broadcast(msg, time):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO broadcasts (message, time) VALUES (?, ?)", (msg, time))
    conn.commit()
    conn.close()

def get_broadcasts():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT message, time FROM broadcasts ORDER BY id ASC")
    result = c.fetchall()
    conn.close()
    return result