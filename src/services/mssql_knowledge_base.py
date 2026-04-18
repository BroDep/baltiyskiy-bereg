from __future__ import annotations

import logging
from datetime import datetime

import pymssql

from src.config import Settings
from src.services.rag_models import RagDocument
from src.services.text_normalization import (
    build_excerpt,
    chunk_text,
    cleanup_html,
    make_content_hash,
    make_point_id,
    normalize_lookup_value,
    trim_text,
)

logger = logging.getLogger(__name__)


class MSSQLKnowledgeBase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch_ticket_batch_after_id(
        self,
        last_id: int,
        batch_size: int,
    ) -> list[RagDocument]:
        query = f"""
        SELECT TOP {int(batch_size)}
            t.Id,
            t.ParentId,
            t.Name,
            t.Description,
            t.Comment,
            t.Created,
            t.Changed,
            t.Closed,
            t.StatusId,
            t.PriorityId,
            t.ServiceId,
            t.TypeId,
            st.NameXml AS StatusNameXml,
            pr.NameXml AS PriorityNameXml,
            sv.NameXml AS ServiceNameXml,
            tt.NameXml AS TaskTypeNameXml
        FROM Task AS t
        LEFT JOIN Status AS st ON st.Id = t.StatusId
        LEFT JOIN Priority AS pr ON pr.Id = t.PriorityId
        LEFT JOIN Service AS sv ON sv.Id = t.ServiceId
        LEFT JOIN TaskType AS tt ON tt.Id = t.TypeId
        WHERE t.Id > %s
        ORDER BY t.Id
        """
        rows = self._fetch_all(query, (last_id,))
        return self._build_ticket_documents(rows)

    def fetch_kb_batch_after_id(
        self,
        last_id: int,
        batch_size: int,
    ) -> list[RagDocument]:
        query = f"""
        SELECT TOP {int(batch_size)}
            Id,
            ParentId,
            Name,
            Description,
            CreateDate,
            ChangeDate,
            PublishDate,
            IsPublished,
            Rating
        FROM KBDocument
        WHERE IsPublished = 1 AND Id > %s
        ORDER BY Id
        """
        rows = self._fetch_all(query, (last_id,))
        return self._build_kb_documents(rows)

    def fetch_ticket_documents_changed_after(
        self,
        changed_after: datetime,
    ) -> list[RagDocument]:
        query = """
        SELECT
            t.Id,
            t.ParentId,
            t.Name,
            t.Description,
            t.Comment,
            t.Created,
            t.Changed,
            t.Closed,
            t.StatusId,
            t.PriorityId,
            t.ServiceId,
            t.TypeId,
            st.NameXml AS StatusNameXml,
            pr.NameXml AS PriorityNameXml,
            sv.NameXml AS ServiceNameXml,
            tt.NameXml AS TaskTypeNameXml
        FROM Task AS t
        LEFT JOIN Status AS st ON st.Id = t.StatusId
        LEFT JOIN Priority AS pr ON pr.Id = t.PriorityId
        LEFT JOIN Service AS sv ON sv.Id = t.ServiceId
        LEFT JOIN TaskType AS tt ON tt.Id = t.TypeId
        WHERE COALESCE(t.Changed, t.Created) > %s
        ORDER BY COALESCE(t.Changed, t.Created), t.Id
        """
        rows = self._fetch_all(query, (changed_after,))
        return self._build_ticket_documents(rows)

    def fetch_kb_documents_changed_after(
        self,
        changed_after: datetime,
    ) -> list[RagDocument]:
        query = """
        SELECT
            Id,
            ParentId,
            Name,
            Description,
            CreateDate,
            ChangeDate,
            PublishDate,
            IsPublished,
            Rating
        FROM KBDocument
        WHERE IsPublished = 1
          AND COALESCE(ChangeDate, PublishDate, CreateDate) > %s
        ORDER BY COALESCE(ChangeDate, PublishDate, CreateDate), Id
        """
        rows = self._fetch_all(query, (changed_after,))
        return self._build_kb_documents(rows)

    def _connect(self) -> pymssql.Connection:
        self._settings.validate_mssql()
        return pymssql.connect(
            server=self._settings.mssql_host,
            port=self._settings.mssql_port,
            user=self._settings.mssql_user,
            password=self._settings.mssql_password_value,
            database=self._settings.mssql_database,
            charset="UTF-8",
            login_timeout=5,
            timeout=60,
            as_dict=True,
        )

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[dict[str, object]]:
        connection = self._connect()
        try:
            with connection.cursor(as_dict=True) as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return list(rows)
        finally:
            connection.close()

    def _fetch_task_expenses(self, task_ids: list[int]) -> dict[int, list[str]]:
        if not task_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(task_ids))
        query = f"""
        SELECT TaskId, Date, Minutes, Comments
        FROM TaskExpenses
        WHERE TaskId IN ({placeholders})
        ORDER BY TaskId, Date
        """
        rows = self._fetch_all(query, tuple(task_ids))
        grouped: dict[int, list[str]] = {task_id: [] for task_id in task_ids}
        for row in rows:
            task_id = int(row["TaskId"])
            comment = cleanup_html(str(row.get("Comments") or ""))
            minutes = row.get("Minutes")
            if not comment and minutes in (None, 0):
                continue
            prefix = f"{int(minutes)} мин" if minutes not in (None, "") else "Работы"
            if comment:
                grouped.setdefault(task_id, []).append(f"{prefix}: {comment}")
            else:
                grouped.setdefault(task_id, []).append(prefix)
        return grouped

    def _fetch_task_fields(self, task_ids: list[int]) -> dict[int, list[str]]:
        if not task_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(task_ids))
        query = f"""
        SELECT
            tfv.EntityId,
            ttf.NameXml AS FieldNameXml,
            tcb.ValueXml AS ComboboxValueXml,
            tfv.Value,
            tfv.NumericValue,
            tfv.DateValue,
            tfv.BitValue
        FROM TaskFieldValues AS tfv
        LEFT JOIN TaskTypeField AS ttf ON ttf.Id = tfv.FieldId
        LEFT JOIN TaskTypeComboBox AS tcb ON tcb.Id = tfv.ComboboxId
        WHERE tfv.DeleteDate IS NULL
          AND tfv.EntityId IN ({placeholders})
        ORDER BY tfv.EntityId, tfv.FieldId
        """
        rows = self._fetch_all(query, tuple(task_ids))
        grouped: dict[int, list[str]] = {task_id: [] for task_id in task_ids}
        for row in rows:
            task_id = int(row["EntityId"])
            field_name = normalize_lookup_value(str(row.get("FieldNameXml") or "")) or "Поле"
            value = self._normalize_task_field_value(row)
            if value:
                grouped.setdefault(task_id, []).append(f"{field_name}: {value}")
        return grouped

    def _normalize_task_field_value(self, row: dict[str, object]) -> str:
        combobox_value = normalize_lookup_value(str(row.get("ComboboxValueXml") or ""))
        if combobox_value:
            return combobox_value

        text_value = cleanup_html(str(row.get("Value") or ""))
        if text_value:
            return text_value

        numeric_value = row.get("NumericValue")
        if numeric_value not in (None, ""):
            return str(numeric_value)

        date_value = row.get("DateValue")
        if isinstance(date_value, datetime):
            return date_value.isoformat(sep=" ", timespec="minutes")

        bit_value = row.get("BitValue")
        if bit_value is not None:
            return "Да" if bool(bit_value) else "Нет"

        return ""

    def _build_ticket_documents(self, rows: list[dict[str, object]]) -> list[RagDocument]:
        if not rows:
            return []

        task_ids = [int(row["Id"]) for row in rows]
        expenses_by_task = self._fetch_task_expenses(task_ids)
        fields_by_task = self._fetch_task_fields(task_ids)
        documents: list[RagDocument] = []

        for row in rows:
            task_id = int(row["Id"])
            title = cleanup_html(str(row.get("Name") or "")) or f"Заявка {task_id}"
            description = cleanup_html(str(row.get("Description") or ""))
            comment = cleanup_html(str(row.get("Comment") or ""))
            status_name = normalize_lookup_value(str(row.get("StatusNameXml") or ""))
            priority_name = normalize_lookup_value(str(row.get("PriorityNameXml") or ""))
            service_name = normalize_lookup_value(str(row.get("ServiceNameXml") or ""))
            task_type_name = normalize_lookup_value(str(row.get("TaskTypeNameXml") or ""))

            content_parts = [
                f"Тикет #{task_id}",
                f"Название: {title}",
            ]
            if service_name:
                content_parts.append(f"Сервис: {service_name}")
            if task_type_name:
                content_parts.append(f"Тип заявки: {task_type_name}")
            if status_name:
                content_parts.append(f"Статус: {status_name}")
            if priority_name:
                content_parts.append(f"Приоритет: {priority_name}")
            if description:
                content_parts.append(f"Описание: {description}")
            if comment:
                content_parts.append(f"Переписка: {comment}")

            task_fields = fields_by_task.get(task_id, [])
            if task_fields:
                content_parts.append("Кастомные поля: " + "; ".join(task_fields[:40]))

            expenses = expenses_by_task.get(task_id, [])
            if expenses:
                content_parts.append("Работы: " + "; ".join(expenses[:25]))

            content = trim_text("\n".join(content_parts), self._settings.rag_ticket_max_chars)
            changed_at = self._coalesce_datetime(row.get("Changed"), row.get("Created"))
            metadata = {
                "content_hash": make_content_hash(title, description, comment, content),
                "parent_id": row.get("ParentId"),
                "status_id": row.get("StatusId"),
                "priority_id": row.get("PriorityId"),
                "service_id": row.get("ServiceId"),
                "task_type_id": row.get("TypeId"),
                "status_name": status_name,
                "priority_name": priority_name,
                "service_name": service_name,
                "task_type_name": task_type_name,
                "created_at": self._datetime_to_iso(row.get("Created")),
                "changed_at": self._datetime_to_iso(changed_at),
                "closed_at": self._datetime_to_iso(row.get("Closed")),
                "is_closed": bool(row.get("Closed")),
            }
            documents.append(
                RagDocument(
                    point_id=make_point_id("ticket", task_id),
                    source_type="ticket",
                    source_id=task_id,
                    chunk_index=0,
                    title=title,
                    content=content,
                    citation_label=f"TICKET#{task_id}",
                    excerpt=build_excerpt(content),
                    metadata=metadata,
                    changed_at=changed_at,
                )
            )

        return documents

    def _build_kb_documents(self, rows: list[dict[str, object]]) -> list[RagDocument]:
        documents: list[RagDocument] = []
        for row in rows:
            kb_id = int(row["Id"])
            title = cleanup_html(str(row.get("Name") or "")) or f"KB {kb_id}"
            body = cleanup_html(str(row.get("Description") or ""))
            base_text = "\n".join(
                part
                for part in (
                    f"KB #{kb_id}",
                    f"Название: {title}",
                    body,
                )
                if part
            )
            chunks = chunk_text(
                base_text,
                max_chars=self._settings.rag_kb_chunk_size_chars,
                overlap_chars=self._settings.rag_kb_chunk_overlap_chars,
            ) or [f"KB #{kb_id}\nНазвание: {title}"]
            changed_at = self._coalesce_datetime(
                row.get("ChangeDate"),
                row.get("PublishDate"),
                row.get("CreateDate"),
            )
            for chunk_index, chunk in enumerate(chunks):
                metadata = {
                    "content_hash": make_content_hash(title, body, chunk),
                    "parent_id": row.get("ParentId"),
                    "rating": row.get("Rating"),
                    "published": bool(row.get("IsPublished")),
                    "create_date": self._datetime_to_iso(row.get("CreateDate")),
                    "change_date": self._datetime_to_iso(row.get("ChangeDate")),
                    "publish_date": self._datetime_to_iso(row.get("PublishDate")),
                    "changed_at": self._datetime_to_iso(changed_at),
                }
                documents.append(
                    RagDocument(
                        point_id=make_point_id("kb", kb_id, chunk_index),
                        source_type="kb",
                        source_id=kb_id,
                        chunk_index=chunk_index,
                        title=title,
                        content=chunk,
                        citation_label=f"KB#{kb_id}",
                        excerpt=build_excerpt(chunk),
                        metadata=metadata,
                        changed_at=changed_at,
                    )
                )

        return documents

    def _coalesce_datetime(self, *values: object) -> datetime | None:
        for value in values:
            if isinstance(value, datetime):
                return value
        return None

    def _datetime_to_iso(self, value: object) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return None
