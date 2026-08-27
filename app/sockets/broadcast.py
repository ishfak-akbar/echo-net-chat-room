from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models.broadcast import Broadcast

GLOBAL_ROOM = "global"


@socketio.on("send_broadcast")
def handle_send_broadcast(data):
    if not current_user.is_authenticated or not current_user.is_admin:
        emit("error", {"message": "Admin privileges required."})
        return

    content = (data.get("content") or "").strip()
    if not content:
        emit("error", {"message": "Broadcast content is required."})
        return

    broadcast = Broadcast(admin_id=current_user.id, content=content)
    db.session.add(broadcast)
    db.session.commit()

    emit("new_broadcast", broadcast.to_dict(), room=GLOBAL_ROOM)


@socketio.on("get_broadcast_history")
def handle_get_broadcast_history(data):
    if not current_user.is_authenticated:
        return

    limit = min(int((data or {}).get("limit", 20)), 50)

    broadcasts = (
        Broadcast.query.order_by(Broadcast.created_at.desc())
        .limit(limit)
        .all()
    )
    broadcasts.reverse()

    emit("broadcast_history", {"broadcasts": [b.to_dict() for b in broadcasts]})