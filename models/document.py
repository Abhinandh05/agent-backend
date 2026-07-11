# backend/models/document.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="uploaded")
    # status: uploaded | processing | indexed | failed
    chunk_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="documents")

    def __repr__(self):
        return f"<Document id={self.id} filename={self.filename!r} status={self.status}>"
