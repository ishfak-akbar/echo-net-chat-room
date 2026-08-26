from datetime import datetime, timezone
from app import db


class TimestampMixin:
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )