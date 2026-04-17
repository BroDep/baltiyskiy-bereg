"""Generate 1000 test chat sessions with realistic distributions.

Usage:
    python seed_data.py
"""
from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta

os.makedirs("data", exist_ok=True)

from src.db.database import SessionLocal, init_db  # noqa: E402
from src.db.models import ChatSession  # noqa: E402

# ── Sample messages by category ──────────────────────────────────────────────
CATEGORIES = [
    {
        "weight": 0.22,
        "resolve_rate": 0.82,
        "messages": [
            "Не работает VPN, не могу подключиться к корпоративной сети",
            "После обновления Windows VPN перестал работать",
            "Как настроить удалённый доступ на новом ноутбуке?",
            "VPN подключается, но нет доступа к внутренним ресурсам",
            "Какой клиент VPN использовать для Mac?",
        ],
        "answers": [
            "Установите UniVPN с portal.company.ru, сервер vpn.company.ru, логин доменный.",
            "Обновите клиент UniVPN до актуальной версии, ссылка на portal.company.ru.",
            "Инструкция по настройке удалённого доступа отправлена на почту.",
        ],
    },
    {
        "weight": 0.20,
        "resolve_rate": 0.90,
        "messages": [
            "Забыл пароль от Windows, как сбросить?",
            "Заблокировалась учётная запись в Active Directory",
            "Не помню пароль от корпоративной почты",
            "Как сменить истёкший пароль не заходя в систему?",
            "Учётная запись заблокирована после нескольких попыток входа",
        ],
        "answers": [
            "Сбросьте пароль через password.company.ru, подтвердите через корп. почту.",
            "Учётная запись разблокирована, новый пароль отправлен на корп. почту.",
            "Для смены пароля воспользуйтесь порталом password.company.ru.",
        ],
    },
    {
        "weight": 0.15,
        "resolve_rate": 0.74,
        "messages": [
            "Принтер не печатает, документ завис в очереди",
            "Не сканируется документ, ошибка подключения к сканеру",
            "Нужно установить драйвер для принтера HP LaserJet",
            "После замены картриджа принтер не определяет его",
            "Принтер печатает с полосами, нужна чистка",
        ],
        "answers": [
            "Очистите очередь печати, переустановите драйвер с drivers.company.ru.",
            "Специалист придёт для настройки принтера в течение 2 часов.",
            "Драйвер установлен удалённо, принтер должен работать.",
        ],
    },
    {
        "weight": 0.12,
        "resolve_rate": 0.68,
        "messages": [
            "1С не запускается, ошибка при старте",
            "Нет доступа к базе 1С после смены пароля",
            "1С работает очень медленно с утра",
            "Ошибка лицензии при запуске 1С",
            "Не открываются документы в 1С, вылетает",
        ],
        "answers": [
            "Перезапустите службу 1C:Enterprise через services.msc.",
            "Доступ к базе восстановлен, синхронизированы учётные данные.",
            "Проблема с лицензией передана администратору 1С.",
        ],
    },
    {
        "weight": 0.14,
        "resolve_rate": 0.77,
        "messages": [
            "Не открывается Excel, вылетает при запуске",
            "Нужно установить Microsoft Office на новый компьютер",
            "Обновление Office завершилось с ошибкой 0x80070005",
            "Teams не показывает статус онлайн у коллег",
            "Outlook не синхронизирует почту",
        ],
        "answers": [
            "Office переустановлен с корпоративного портала, проблема решена.",
            "Лицензия активирована, Office установлен на устройство.",
            "Ошибка Teams устранена сбросом кэша приложения.",
        ],
    },
    {
        "weight": 0.17,
        "resolve_rate": 0.55,
        "messages": [
            "Нет доступа к сетевой папке \\\\fileserver\\shared",
            "Не могу войти на корпоративный портал",
            "Нужен доступ к системе SAP для нового сотрудника",
            "Монитор показывает чёрный экран при включении",
            "Не работает USB-порт на ноутбуке",
            "Интернет очень медленный, что-то случилось с сетью?",
            "Компьютер не включается, нет реакции при нажатии кнопки",
        ],
        "answers": [
            "Доступ к сетевой папке предоставлен, обратитесь если ошибка повторится.",
            "Заявка передана ответственному за систему, ожидайте решения.",
            "Специалист выедет для диагностики оборудования.",
        ],
    },
]

ESCALATION_ANSWER = (
    "Ваш запрос передан специалисту технической поддержки. "
    "Ожидайте ответа в течение 1 рабочего дня. "
    "Для срочных вопросов: +7 (812) 000-00-01."
)


def gauss_hour() -> int:
    """Work-hours normal distribution centred at 10:30."""
    while True:
        h = int(random.gauss(10.5, 2.5))
        if 7 <= h <= 21:
            return h


def weighted_day(base: datetime, span: int = 90) -> int:
    """Pick a day offset weighted toward weekdays."""
    weights = []
    for d in range(span):
        wd = (base + timedelta(days=d)).weekday()
        weights.append(1.0 if wd < 5 else 0.25)
    total = sum(weights)
    r = random.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return i
    return span - 1


def main() -> None:
    init_db()
    db = SessionLocal()

    base = datetime.utcnow() - timedelta(days=90)

    records: list[ChatSession] = []
    for _ in range(1000):
        cat = random.choices(CATEGORIES, weights=[c["weight"] for c in CATEGORIES])[0]
        escalated = random.random() > cat["resolve_rate"]

        if escalated:
            conf = round(random.gauss(3.5, 1.0), 1)
            conf = max(0.0, min(6.9, conf))
            label = "low" if conf < 5 else "medium"
            answer = ESCALATION_ANSWER
        else:
            conf = round(random.gauss(7.8, 1.2), 1)
            conf = max(5.0, min(10.0, conf))
            label = "high" if conf >= 8 else "medium"
            answer = random.choice(cat["answers"])

        day_offset = weighted_day(base)
        hour = gauss_hour()
        created_at = base + timedelta(
            days=day_offset,
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        records.append(
            ChatSession(
                session_id=str(uuid.uuid4()),
                message=random.choice(cat["messages"]),
                answer=answer,
                confidence_score=conf,
                confidence_label=label,
                escalated=escalated,
                created_at=created_at,
            )
        )

    db.bulk_save_objects(records)
    db.commit()
    db.close()

    total = len(records)
    escalated_count = sum(1 for r in records if r.escalated)
    print(f"Seeded {total} records  |  escalated: {escalated_count} ({escalated_count/total*100:.1f}%)")


if __name__ == "__main__":
    main()
