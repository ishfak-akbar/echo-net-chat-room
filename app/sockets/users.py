from flask_login import current_user
from flask_socketio import emit
from app import socketio
from app.models.user import User


@socketio.on("get_all_users")
def handle_get_all_users():
    if not current_user.is_authenticated:
        return

    users = User.query.filter(User.id != current_user.id).all()
    emit("all_users", {"users": [u.to_public_dict() for u in users]})