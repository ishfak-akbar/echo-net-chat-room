from flask import request
from flask_login import current_user
from flask_socketio import join_room, emit
from app import socketio, db
from app.models.user import User
from app.models.ban import Ban
from app.sockets.state import add_connection, remove_connection

PRESENCE_ROOM = "presence"
GLOBAL_ROOM = "global"


def _user_room(user_id: int) -> str:
    return f"user_{user_id}"


@socketio.on("connect")
def handle_connect():
    if not current_user.is_authenticated:
        return False  # refuses the connection outright

    active_ban = Ban.query.filter_by(user_id=current_user.id, is_active=True).first()
    if active_ban:
        return False

    join_room(_user_room(current_user.id))
    join_room(PRESENCE_ROOM)
    join_room(GLOBAL_ROOM)

    count = add_connection(current_user.id, request.sid)

    if count == 1:
        current_user.is_online = True
        db.session.commit()
        emit(
            "presence_update",
            {"user_id": current_user.id, "username": current_user.username, "is_online": True},
            room=PRESENCE_ROOM,
            include_self=False,
        )

    online_users = User.query.filter_by(is_online=True).all()
    emit(
        "online_users_snapshot",
        {"users": [u.to_public_dict() for u in online_users]},
    )


@socketio.on("disconnect")
def handle_disconnect():
    if not current_user.is_authenticated:
        return

    remaining = remove_connection(current_user.id, request.sid)

    if remaining == 0:
        current_user.is_online = False
        current_user.touch_last_seen()
        db.session.commit()
        emit(
            "presence_update",
            {"user_id": current_user.id, "username": current_user.username, "is_online": False},
            room=PRESENCE_ROOM,
        )