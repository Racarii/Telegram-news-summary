"""Вызовы внешнего API DeepSeek для построения саммари."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Sequence

import httpx


class SummarizationError(RuntimeError):
    """Ошибка при генерации саммари."""


@dataclass
class SummaryRequest:
    """Описывает один запрос на саммаризацию."""

    title: str
    text: str


class DeepSeekSummarizer:
    """Клиент для обращения к DeepSeek Chat Completions API."""

    API_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "deepseek-chat", language: str = "ru") -> None:
        self._api_key = api_key
        self._model = model
        self._language = language
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def summarize(self, requests: Sequence[SummaryRequest]) -> Sequence[str]:
        """Последовательно вызывает API для каждого запроса.

        На MVP этапе выполняем вызовы последовательно, чтобы проще уложиться в лимиты.
        """

        outputs: list[str] = []
        for req in requests:
            outputs.append(await self._summarize_single(req))
        return outputs

    async def _summarize_single(self, request: SummaryRequest) -> str:
        """Отправляет запрос в DeepSeek и возвращает текст ответа."""

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты помощник, который делает лаконичные, структурированные отчёты на русском языке. "
                        "Сохраняй факты, избегай воды, используй Markdown-списки, если уместно."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Сформируй краткое недельное саммари для блока '{request.title}'. "
                        "Вытащи ключевые новости, цифры, имена и объясни контекст. "
                        "Если несколько тем, сгруппируй их в маркированный список.\n\n"
                        f"Исходные сообщения:\n{request.text}"
                    ),
                },
            ],
            "temperature": 0.3,
        }

        response = await self._client.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code != 200:
            raise SummarizationError(
                f"DeepSeek вернул статус {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:  # pragma: no cover - защита от неожиданных структур
            raise SummarizationError(f"Неожиданная структура ответа: {data}") from exc


async def summarize_batches(
    summarizer: DeepSeekSummarizer,
    batches: Iterable[SummaryRequest],
) -> Sequence[str]:
    """Утилита для лаконичного вызова summarize в асинхронном коде."""

    return await summarizer.summarize(list(batches))


__all__ = [
    "DeepSeekSummarizer",
    "SummarizationError",
    "SummaryRequest",
    "summarize_batches",
]
