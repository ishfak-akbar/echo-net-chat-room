from flask_login import current_user
from flask_socketio import emit, disconnect
from app import socketio, db
from app.models.user import User
from app.models.ban import Ban
from app.models.message import DirectMessage, GlobalMessage
from app.models.group import Group, GroupMessage
from app.models.broadcast import Broadcast
from app.sockets.state import user_sids

PRESENCE_ROOM = "presence"


def _require_admin() -> bool:
    return current_user.is_authenticated and current_user.is_admin


def _force_disconnect_user(user_id: int) -> None:
    for sid in list(user_sids.get(user_id, set())):
        disconnect(sid=sid)


@socketio.on("kick_user")
def handle_kick_user(data):
    if not _require_admin():
        emit("error", {"message": "Admin privileges required."})
        return

    target = User.query.get(data.get("user_id"))
    if not target:
        emit("error", {"message": "User not found."})
        return
    if target.is_admin:
        emit("error", {"message": "Cannot kick another admin."})
        return

    _force_disconnect_user(target.id)

    emit(
        "admin_action",
        {"action": "kick", "user_id": target.id, "username": target.username},
        room=PRESENCE_ROOM,
    )


@socketio.on("ban_user")
def handle_ban_user(data):
    if not _require_admin():
        emit("error", {"message": "Admin privileges required."})
        return

    target = User.query.get(data.get("user_id"))
    if not target:
        emit("error", {"message": "User not found."})
        return
    if target.is_admin:
        emit("error", {"message": "Cannot ban another admin."})
        return

    if Ban.query.filter_by(user_id=target.id, is_active=True).first():
        emit("error", {"message": "User is already banned."})
        return

    reason = (data.get("reason") or "").strip() or None
    ban = Ban(user_id=target.id, banned_by=current_user.id, reason=reason, is_active=True)
    db.session.add(ban)
    db.session.commit()

    _force_disconnect_user(target.id)

    emit(
        "admin_action",
        {"action": "ban", "user_id": target.id, "username": target.username, "reason": reason},
        room=PRESENCE_ROOM,
    )


@socketio.on("unban_user")
def handle_unban_user(data):
    if not _require_admin():
        emit("error", {"message": "Admin privileges required."})
        return

    target_id = data.get("user_id")
    active_bans = Ban.query.filter_by(user_id=target_id, is_active=True).all()
    if not active_bans:
        emit("error", {"message": "User is not currently banned."})
        return

    for ban in active_bans:
        ban.is_active = False
    db.session.commit()

    target = User.query.get(target_id)
    emit(
        "admin_action",
        {"action": "unban", "user_id": target_id, "username": target.username if target else None},
        room=PRESENCE_ROOM,
    )


@socketio.on("get_banned_users")
def handle_get_banned_users():
    if not _require_admin():
        emit("error", {"message": "Admin privileges required."})
        return

    active_bans = Ban.query.filter_by(is_active=True).all()
    result = [
        {
            "user_id": b.user_id,
            "username": b.user.username if b.user else None,
            "banned_by": b.admin.username if b.admin else None,
            "reason": b.reason,
            "banned_at": b.created_at.isoformat(),
        }
        for b in active_bans
    ]
    emit("banned_users", {"bans": result})


@socketio.on("get_admin_stats")
def handle_get_admin_stats():
    if not _require_admin():
        emit("error", {"message": "Admin privileges required."})
        return

    stats = {
        "total_users": User.query.count(),
        "online_users": User.query.filter_by(is_online=True).count(),
        "total_groups": Group.query.count(),
        "total_dm_messages": DirectMessage.query.count(),
        "total_group_messages": GroupMessage.query.count(),
        "total_global_messages": GlobalMessage.query.count(),
        "total_broadcasts": Broadcast.query.count(),
        "active_bans": Ban.query.filter_by(is_active=True).count(),
    }
    emit("admin_stats", stats)