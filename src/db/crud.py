from __future__ import annotations

import hashlib
import json
import os as _os
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from src.db.models import ChatSession, Message, User


# ── Password helpers ──────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = _os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
        return key.hex() == key_hex
    except Exception:
        return False


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_or_create(db: Session, username: str, password: str) -> tuple[User | None, str]:
    """Return (user, status) where status is 'created' | 'ok' | 'wrong_password'."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        user = User(username=username, password_hash=_hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, "created"
    if _verify_password(password, user.password_hash):
        return user, "ok"
    return None, "wrong_password"


# ── Message history ───────────────────────────────────────────────────────────

def save_message(
    db: Session,
    *,
    user_id: int,
    role: str,
    content: str,
    meta: Any | None = None,
) -> Message:
    msg = Message(
        user_id=user_id,
        role=role,
        content=content,
        meta=json.dumps(meta, ensure_ascii=False) if meta is not None else None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_history(
    db: Session,
    *,
    user_id: int,
    before_id: int | None = None,
    limit: int = 20,
) -> tuple[list[Message], bool]:
    q = db.query(Message).filter(Message.user_id == user_id)
    if before_id is not None:
        q = q.filter(Message.id < before_id)
    total = q.count()
    rows = q.order_by(Message.id.desc()).limit(limit).all()
    rows.reverse()
    return rows, total > limit


# ── Analytics session ─────────────────────────────────────────────────────────

def save_session(
    db: Session,
    *,
    session_id: str,
    message: str,
    answer: str,
    confidence_score: float,
    confidence_label: str,
    escalated: bool,
) -> ChatSession:
    obj = ChatSession(
        session_id=session_id,
        message=message,
        answer=answer,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        escalated=escalated,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _apply_date_filter(q, date_from: Optional[datetime], date_to: Optional[datetime]):
    if date_from:
        q = q.filter(ChatSession.created_at >= date_from)
    if date_to:
        q = q.filter(ChatSession.created_at <= date_to)
    return q


def get_stats(db: Session, date_from=None, date_to=None) -> dict:
    q = _apply_date_filter(db.query(ChatSession), date_from, date_to)
    total = q.count()
    escalated = q.filter(ChatSession.escalated.is_(True)).count()
    avg_conf = _apply_date_filter(db.query(func.avg(ChatSession.confidence_score)), date_from, date_to).scalar() or 0.0
    return {
        "total": total,
        "resolved": total - escalated,
        "escalated": escalated,
        "escalation_rate": round(escalated / total * 100, 1) if total else 0.0,
        "avg_confidence": round(float(avg_conf), 1),
    }


def get_hourly(db: Session, date_from=None, date_to=None) -> list[dict]:
    q = _apply_date_filter(
        db.query(func.strftime("%H", ChatSession.created_at).label("hour"), func.count().label("count")),
        date_from, date_to,
    )
    counts = {int(r.hour): r.count for r in q.group_by("hour").all()}
    return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]


def get_daily_failures(db: Session, days: int = 30, date_from=None, date_to=None) -> list[dict]:
    q = db.query(
        func.strftime("%Y-%m-%d", ChatSession.created_at).label("date"),
        func.count().label("total"),
        func.sum(cast(ChatSession.escalated, Integer)).label("escalated"),
    )
    if date_from or date_to:
        q = _apply_date_filter(q, date_from, date_to)
    else:
        q = q.filter(ChatSession.created_at >= datetime.utcnow() - timedelta(days=days))
    rows = q.group_by("date").order_by("date").all()
    return [{"date": r.date, "total": r.total, "escalated": r.escalated or 0} for r in rows]


def get_tickets(db: Session, *, page=1, limit=20, search="", status="all", date_from=None, date_to=None) -> dict:
    q = _apply_date_filter(db.query(ChatSession), date_from, date_to)
    if search:
        q = q.filter(ChatSession.message.ilike(f"%{search}%"))
    if status == "resolved":
        q = q.filter(ChatSession.escalated.is_(False))
    elif status == "escalated":
        q = q.filter(ChatSession.escalated.is_(True))
    total = q.count()
    items = q.order_by(ChatSession.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "pages": max(1, (total + limit - 1) // limit), "items": items}
