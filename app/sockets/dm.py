from datetime import datetime, timezone
from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models.user import User
from app.models.message import DirectMessage


def _user_room(user_id: int) -> str:
    return f"user_{user_id}"


@socketio.on("send_dm")
def handle_send_dm(data):
    if not current_user.is_authenticated:
        return

    receiver_id = data.get("receiver_id")
    content = (data.get("content") or "").strip()
    image_url = data.get("image_url")

    if not receiver_id or (not content and not image_url):
        emit("error", {"message": "receiver_id and content or image_url are required."})
        return

    if receiver_id == current_user.id:
        emit("error", {"message": "Cannot send a DM to yourself."})
        return

    receiver = User.query.get(receiver_id)
    if not receiver:
        emit("error", {"message": "Receiver not found."})
        return

    message = DirectMessage(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content or None,
        image_url=image_url,
    )
    db.session.add(message)
    db.session.commit()

    payload = message.to_dict()
    emit("new_dm", payload, room=_user_room(receiver_id))
    emit("new_dm", payload, room=_user_room(current_user.id))  # sync sender's other devices


@socketio.on("mark_dm_read")
def handle_mark_dm_read(data):
    if not current_user.is_authenticated:
        return

    other_user_id = data.get("sender_id")
    if not other_user_id:
        return

    unread = DirectMessage.query.filter_by(
        sender_id=other_user_id, receiver_id=current_user.id, is_read=False
    ).all()

    if not unread:
        return

    now = datetime.now(timezone.utc)
    message_ids = []
    for msg in unread:
        msg.is_read = True
        msg.read_at = now
        message_ids.append(msg.id)
    db.session.commit()

    emit(
        "dm_read_receipt",
        {"reader_id": current_user.id, "message_ids": message_ids},
        room=_user_room(other_user_id),
    )


@socketio.on("get_dm_history")
def handle_get_dm_history(data):
    if not current_user.is_authenticated:
        return

    other_user_id = data.get("other_user_id")
    if not other_user_id:
        emit("error", {"message": "other_user_id is required."})
        return

    limit = min(int(data.get("limit", 50)), 100)

    messages = (
        DirectMessage.query.filter(
            db.or_(
                db.and_(
                    DirectMessage.sender_id == current_user.id,
                    DirectMessage.receiver_id == other_user_id,
                ),
                db.and_(
                    DirectMessage.sender_id == other_user_id,
                    DirectMessage.receiver_id == current_user.id,
                ),
            )
        )
        .order_by(DirectMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()

    emit(
        "dm_history",
        {"other_user_id": other_user_id, "messages": [m.to_dict() for m in messages]},
    )