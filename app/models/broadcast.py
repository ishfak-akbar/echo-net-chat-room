from app import db
from app.models.mixins import TimestampMixin


class Broadcast(db.Model, TimestampMixin):
    __tablename__ = "broadcasts"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)

    admin = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin_username": self.admin.username if self.admin else None,
            "content": self.content,
            "timestamp": self.created_at.isoformat(),
        }