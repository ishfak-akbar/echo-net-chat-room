from flask_login import current_user
from flask_socketio import join_room, emit
from app import socketio, db
from app.models.user import User
from app.sockets.state import connection_counts

PRESENCE_ROOM = "presence"
GLOBAL_ROOM = "global"


def _user_room(user_id: int) -> str:
    return f"user_{user_id}"


@socketio.on("connect")
def handle_connect():
    if not current_user.is_authenticated:
        return False  # refuses the connection outright

    join_room(_user_room(current_user.id))
    join_room(PRESENCE_ROOM)
    join_room(GLOBAL_ROOM)

    connection_counts[current_user.id] = connection_counts.get(current_user.id, 0) + 1

    # First active connection for this user -> they just came online
    if connection_counts[current_user.id] == 1:
        current_user.is_online = True
        db.session.commit()
        emit(
            "presence_update",
            {"user_id": current_user.id, "username": current_user.username, "is_online": True},
            room=PRESENCE_ROOM,
            include_self=False,
        )

    # Send the freshly-connected client a snapshot of who's currently online
    online_users = User.query.filter_by(is_online=True).all()
    emit(
        "online_users_snapshot",
        {"users": [u.to_public_dict() for u in online_users]},
    )


@socketio.on("disconnect")
def handle_disconnect():
    if not current_user.is_authenticated:
        return

    user_id = current_user.id
    connection_counts[user_id] = max(0, connection_counts.get(user_id, 0) - 1)

    # Only mark offline once ALL of this user's tabs/devices have disconnected
    if connection_counts[user_id] == 0:
        current_user.is_online = False
        current_user.touch_last_seen()
        db.session.commit()
        emit(
            "presence_update",
            {"user_id": user_id, "username": current_user.username, "is_online": False},
            room=PRESENCE_ROOM,
        )