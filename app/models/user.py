from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.mixins import TimestampMixin


class User(db.Model, UserMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    profile_pic = db.Column(db.String(255), nullable=True)

    is_online = db.Column(db.Boolean, default=False, nullable=False)
    last_seen = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def touch_last_seen(self) -> None:
        self.last_seen = datetime.now(timezone.utc)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "is_admin": self.is_admin,
            "profile_pic": self.profile_pic,
            "is_online": self.is_online,
        }

    def __repr__(self):
        return f"<User {self.username}>"