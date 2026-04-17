from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from src.db.models import ChatSession


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


def get_stats(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    q = _apply_date_filter(db.query(ChatSession), date_from, date_to)
    total = q.count()
    escalated = q.filter(ChatSession.escalated.is_(True)).count()
    avg_conf = db.query(func.avg(ChatSession.confidence_score))
    avg_conf = _apply_date_filter(avg_conf, date_from, date_to).scalar() or 0.0
    resolved = total - escalated
    return {
        "total": total,
        "resolved": resolved,
        "escalated": escalated,
        "escalation_rate": round(escalated / total * 100, 1) if total else 0.0,
        "avg_confidence": round(float(avg_conf), 1),
    }


def get_hourly(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[dict]:
    q = db.query(
        func.strftime("%H", ChatSession.created_at).label("hour"),
        func.count().label("count"),
    )
    q = _apply_date_filter(q, date_from, date_to)
    rows = q.group_by("hour").all()
    counts = {int(r.hour): r.count for r in rows}
    return [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]


def get_daily_failures(
    db: Session,
    days: int = 30,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[dict]:
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


def get_tickets(
    db: Session,
    *,
    page: int = 1,
    limit: int = 20,
    search: str = "",
    status: str = "all",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    q = db.query(ChatSession)
    q = _apply_date_filter(q, date_from, date_to)
    if search:
        q = q.filter(ChatSession.message.ilike(f"%{search}%"))
    if status == "resolved":
        q = q.filter(ChatSession.escalated.is_(False))
    elif status == "escalated":
        q = q.filter(ChatSession.escalated.is_(True))
    total = q.count()
    items = (
        q.order_by(ChatSession.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "items": items,
    }
