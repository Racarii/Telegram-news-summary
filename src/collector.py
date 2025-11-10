"""Модуль для сбора сообщений из Telegram-каналов."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, Any

from telethon import TelegramClient
from telethon.tl.custom.message import Message


@dataclass
class CollectedMessage:
    """Структура данных для хранения сообщений, которые попадут в саммари."""

    channel: str
    message_id: int
    date: dt.datetime
    text: str
    link: str | None
    views: int | None


async def fetch_channel_messages(
    client: TelegramClient,
    channel_entity: Any,
    channel_label: str,
    days_back: int,
    min_chars: int = 50,
) -> List[CollectedMessage]:
    """Собирает сообщения за указанный период.

    Args:
        client: авторизованный TelegramClient.
        channel_entity: объект канала/чата, полученный через client.get_entity.
        channel_label: отображаемое название канала для логов и отчёта.
        days_back: глубина истории в днях.
        min_chars: минимальная длина текста, чтобы избежать спама/шапок.
    """

    now_utc = dt.datetime.now(dt.timezone.utc)
    cutoff = now_utc - dt.timedelta(days=days_back)
    collected: List[CollectedMessage] = []

    async for message in client.iter_messages(channel_entity, offset_date=None):
        if not isinstance(message, Message):
            continue
        if not message.date:
            continue

        message_date = message.date
        if message_date.tzinfo is None:
            message_date = message_date.replace(tzinfo=dt.timezone.utc)
        else:
            message_date = message_date.astimezone(dt.timezone.utc)

        if message_date < cutoff:
            # История отсортирована по убыванию, можно завершать сбор.
            break

        text = (message.message or "").strip()
        if len(text) < min_chars:
            continue

        entity_username = getattr(channel_entity, "username", None)
        message_link: str | None = None
        if entity_username:
            message_link = f"https://t.me/{entity_username}/{message.id}"

        collected.append(
            CollectedMessage(
                channel=channel_label,
                message_id=message.id,
                date=message_date,
                text=text,
                link=message_link,
                views=getattr(message, "views", None),
            )
        )

    return collected


def iterate_channels(raw_lines: Iterable[str]) -> Iterable[str]:
    """Фильтрует список каналов, игнорируя пустые строки и комментарии."""

    for line in raw_lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        yield candidate


__all__ = ["CollectedMessage", "fetch_channel_messages", "iterate_channels"]
