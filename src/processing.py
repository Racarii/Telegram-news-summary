"""Вспомогательные функции для подготовки данных к саммаризации."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List

from .collector import CollectedMessage
from .summarizer import SummaryRequest


MAX_CHARS_PER_REQUEST = 3500
DEFAULT_TOP_MESSAGES = 25


def _format_message(msg: CollectedMessage) -> str:
    date_str = msg.date.strftime("%d.%m %H:%M") if msg.date else ""
    link_part = f" (ссылка: {msg.link})" if msg.link else ""
    views_part = f" [просмотры: {msg.views}]" if msg.views else ""
    return f"- [{date_str}]{views_part}{link_part}\n{msg.text.strip()}"


def select_top_messages(messages: List[CollectedMessage], limit: int = DEFAULT_TOP_MESSAGES) -> List[CollectedMessage]:
    """Отбирает наиболее важные сообщения для передачи в модель.

    Сортируем по числу просмотров (если есть), иначе по дате.
    """

    def sort_key(msg: CollectedMessage) -> tuple[int, dt.datetime]:
        return (msg.views or 0, msg.date)

    return sorted(messages, key=sort_key, reverse=True)[:limit]


def build_summary_request(channel: str, messages: Iterable[CollectedMessage]) -> SummaryRequest:
    """Формирует запрос к модели для одного канала."""

    selected = select_top_messages(list(messages))
    formatted_parts: list[str] = []
    current_chunk_length = 0

    for formatted in (_format_message(msg) for msg in selected):
        candidate_length = current_chunk_length + len(formatted) + 2
        if candidate_length > MAX_CHARS_PER_REQUEST and formatted_parts:
            # Прерываем наполнение, чтобы не превышать лимит.
            break
        formatted_parts.append(formatted)
        current_chunk_length = candidate_length

    digest_text = "\n\n".join(formatted_parts)

    if not digest_text:
        digest_text = "Нет текстовых сообщений подходящей длины за выбранный период."

    title = f"Канал {channel} — недельная сводка"
    return SummaryRequest(title=title, text=digest_text)


def build_overview_request(channel_summaries: List[str]) -> SummaryRequest:
    """Создаёт сводный запрос на основе результатов по каналам."""

    text = "\n\n".join(
        f"Канал {idx + 1}:\n{summary}" for idx, summary in enumerate(channel_summaries)
    )
    return SummaryRequest(title="Общая недельная сводка", text=text)


__all__ = [
    "build_summary_request",
    "build_overview_request",
    "select_top_messages",
    "MAX_CHARS_PER_REQUEST",
]
