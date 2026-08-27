from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models.user import User
from app.models.group import Group, GroupMember, GroupMessage, GroupReadState


def _user_room(user_id: int) -> str:
    return f"user_{user_id}"


def _is_member(group_id: int, user_id: int) -> bool:
    return GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first() is not None


@socketio.on("create_group")
def handle_create_group(data):
    if not current_user.is_authenticated:
        return

    name = (data.get("name") or "").strip()
    member_ids = data.get("member_ids") or []

    if not name or len(name) > 64:
        emit("error", {"message": "Group name is required and must be under 64 characters."})
        return

    if not isinstance(member_ids, list) or not member_ids:
        emit("error", {"message": "At least one member must be added to the group."})
        return

    unique_ids = {int(mid) for mid in member_ids if str(mid).isdigit()}
    unique_ids.add(current_user.id)

    valid_users = User.query.filter(User.id.in_(unique_ids)).all()
    if len(valid_users) < 2:
        emit("error", {"message": "Group needs at least one valid member besides you."})
        return

    group = Group(name=name, created_by=current_user.id)
    db.session.add(group)
    db.session.flush()  # assigns group.id before commit

    for user in valid_users:
        db.session.add(GroupMember(group_id=group.id, user_id=user.id))

    db.session.commit()

    payload = {
        "id": group.id,
        "name": group.name,
        "created_by": group.created_by,
        "member_ids": [u.id for u in valid_users],
    }

    for user in valid_users:
        emit("group_created", payload, room=_user_room(user.id))


@socketio.on("send_group_message")
def handle_send_group_message(data):
    if not current_user.is_authenticated:
        return

    group_id = data.get("group_id")
    content = (data.get("content") or "").strip()
    image_url = data.get("image_url")

    if not group_id or (not content and not image_url):
        emit("error", {"message": "group_id and content or image_url are required."})
        return

    if not _is_member(group_id, current_user.id):
        emit("error", {"message": "You are not a member of this group."})
        return

    message = GroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=content or None,
        image_url=image_url,
    )
    db.session.add(message)
    db.session.commit()

    payload = message.to_dict()

    members = GroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        emit("new_group_message", payload, room=_user_room(member.user_id))


@socketio.on("mark_group_read")
def handle_mark_group_read(data):
    if not current_user.is_authenticated:
        return

    group_id = data.get("group_id")
    if not group_id or not _is_member(group_id, current_user.id):
        return

    latest = (
        GroupMessage.query.filter_by(group_id=group_id)
        .order_by(GroupMessage.id.desc())
        .first()
    )
    if not latest:
        return

    state = GroupReadState.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not state:
        state = GroupReadState(group_id=group_id, user_id=current_user.id)
        db.session.add(state)

    state.last_read_message_id = latest.id
    db.session.commit()


@socketio.on("get_group_history")
def handle_get_group_history(data):
    if not current_user.is_authenticated:
        return

    group_id = data.get("group_id")
    if not group_id or not _is_member(group_id, current_user.id):
        emit("error", {"message": "You are not a member of this group."})
        return

    limit = min(int(data.get("limit", 50)), 100)

    messages = (
        GroupMessage.query.filter_by(group_id=group_id)
        .order_by(GroupMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()

    emit("group_history", {"group_id": group_id, "messages": [m.to_dict() for m in messages]})


@socketio.on("get_my_groups")
def handle_get_my_groups():
    if not current_user.is_authenticated:
        return

    memberships = GroupMember.query.filter_by(user_id=current_user.id).all()
    groups = []
    for gm in memberships:
        group = gm.group
        state = GroupReadState.query.filter_by(group_id=group.id, user_id=current_user.id).first()
        last_read_id = state.last_read_message_id if state else None

        unread_query = GroupMessage.query.filter(GroupMessage.group_id == group.id)
        if last_read_id:
            unread_query = unread_query.filter(GroupMessage.id > last_read_id)
        unread_count = unread_query.filter(GroupMessage.sender_id != current_user.id).count()

        groups.append({
            "id": group.id,
            "name": group.name,
            "member_ids": [m.user_id for m in group.members],
            "unread_count": unread_count,
        })

    emit("my_groups", {"groups": groups})