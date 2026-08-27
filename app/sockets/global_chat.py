from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models.message import GlobalMessage

GLOBAL_ROOM = "global"


@socketio.on("send_global_message")
def handle_send_global_message(data):
    if not current_user.is_authenticated:
        return

    content = (data.get("content") or "").strip()
    image_url = data.get("image_url")

    if not content and not image_url:
        emit("error", {"message": "content or image_url is required."})
        return

    message = GlobalMessage(
        sender_id=current_user.id,
        content=content or None,
        image_url=image_url,
    )
    db.session.add(message)
    db.session.commit()

    emit("new_global_message", message.to_dict(), room=GLOBAL_ROOM)


@socketio.on("get_global_history")
def handle_get_global_history(data):
    if not current_user.is_authenticated:
        return

    limit = min(int((data or {}).get("limit", 50)), 100)

    messages = (
        GlobalMessage.query.order_by(GlobalMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()

    emit("global_history", {"messages": [m.to_dict() for m in messages]})