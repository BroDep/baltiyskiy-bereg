from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)      # "user" | "assistant"
    content = Column(Text, nullable=False)
    meta = Column(Text, nullable=True)             # JSON: confidence, sources, escalate
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), index=True, nullable=False)
    message = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    confidence_label = Column(String(16), nullable=False)
    escalated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
