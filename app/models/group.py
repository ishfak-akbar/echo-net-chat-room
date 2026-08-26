from app import db
from app.models.mixins import TimestampMixin


class Group(db.Model, TimestampMixin):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    creator = db.relationship("User")
    members = db.relationship(
        "GroupMember", backref="group", cascade="all, delete-orphan"
    )
    messages = db.relationship(
        "GroupMessage", backref="group", cascade="all, delete-orphan"
    )


class GroupMember(db.Model, TimestampMixin):
    __tablename__ = "group_members"
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User")


class GroupMessage(db.Model, TimestampMixin):
    __tablename__ = "group_messages"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    content = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)

    sender = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "sender_id": self.sender_id,
            "sender_username": self.sender.username if self.sender else None,
            "content": self.content,
            "image_url": self.image_url,
            "timestamp": self.created_at.isoformat(),
        }


class GroupReadState(db.Model):
    """Tracks the last group message a user has read, for unread counters."""
    __tablename__ = "group_read_states"
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    last_read_message_id = db.Column(
        db.Integer, db.ForeignKey("group_messages.id"), nullable=True
    )