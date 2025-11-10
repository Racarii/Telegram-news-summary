"""Отправка итогового отчёта в Telegram-канал."""

from __future__ import annotations

import httpx


class PublishError(RuntimeError):
    """Ошибка при публикации отчёта."""


class ReportPublisher:
    """Минимальный клиент Telegram Bot API."""

    API_TMPL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def send_markdown(self, chat_id: str, text: str) -> None:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        response = await self._client.post(
            self.API_TMPL.format(token=self._token, method="sendMessage"),
            json=payload,
        )
        data = response.json()
        if response.status_code != 200 or not data.get("ok"):
            raise PublishError(
                f"Не удалось отправить саммари: статус {response.status_code}, ответ: {data}"
            )


__all__ = ["ReportPublisher", "PublishError"]
