# backend/models/task.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    # Manager Agent (Day 16): full plan + step_results JSON for the UI/demo.
    plan_details = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task id={self.id} agent={self.agent_type} status={self.status}>"
