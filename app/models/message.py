from app import db
from app.models.mixins import TimestampMixin


class DirectMessage(db.Model, TimestampMixin):
    __tablename__ = "direct_messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    content = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)

    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "image_url": self.image_url,
            "is_read": self.is_read,
            "timestamp": self.created_at.isoformat(),
        }


class GlobalMessage(db.Model, TimestampMixin):
    __tablename__ = "global_messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    content = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)

    sender = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_username": self.sender.username if self.sender else None,
            "content": self.content,
            "image_url": self.image_url,
            "timestamp": self.created_at.isoformat(),
        }