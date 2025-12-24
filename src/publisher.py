"""Отправка итогового отчёта в Telegram-канал."""

from __future__ import annotations

import asyncio
import logging
import re
import httpx

logger = logging.getLogger(__name__)


def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2 (более строгий формат Telegram)."""
    # Символы, которые нужно экранировать в MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


def clean_markdown(text: str) -> str:
    """Очищает текст от проблемных Markdown конструкций, оставляя простые."""
    # Убираем сложные конструкции, оставляем только простые *жирный* и _курсив_
    # Удаляем незакрытые теги
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)  # **bold** -> *bold*
    text = re.sub(r'__(.*?)__', r'_\1_', text)  # __italic__ -> _italic_
    
    # Убираем одиночные звездочки и подчеркивания, которые могут сломать парсинг
    # Оставляем только пары
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Проверяем, что звездочки/подчеркивания парные
        if line.count('*') % 2 == 0 and line.count('_') % 2 == 0:
            cleaned_lines.append(line)
        else:
            # Убираем проблемные символы
            cleaned_lines.append(line.replace('*', '').replace('_', ''))
    
    return '\n'.join(cleaned_lines)


class PublishError(RuntimeError):
    """Ошибка при публикации отчёта."""


class ReportPublisher:
    """Минимальный клиент Telegram Bot API."""

    API_TMPL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token
        # Увеличиваем таймауты: 60 сек на подключение, 90 сек общий
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=60.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def send_markdown(self, chat_id: str, text: str, max_retries: int = 3) -> None:
        """Отправляет Markdown сообщение с retry-логикой и fallback на обычный текст."""
        
        # Сначала пробуем очищенный Markdown
        cleaned_text = clean_markdown(text)
        
        payload = {
            "chat_id": chat_id,
            "text": cleaned_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug("Попытка %d/%d отправки сообщения (длина: %d символов)", attempt, max_retries, len(text))
                response = await self._client.post(
                    self.API_TMPL.format(token=self._token, method="sendMessage"),
                    json=payload,
                )
                data = response.json()
                
                if response.status_code == 200 and data.get("ok"):
                    logger.debug("Сообщение успешно отправлено")
                    return
                
                error_msg = f"Статус {response.status_code}, ответ: {data}"
                # Если ошибка связана с Markdown, пробуем отправить без форматирования
                if response.status_code == 400 and ("parse" in str(data).lower() or "markdown" in str(data).lower() or "entity" in str(data).lower()):
                    logger.warning("Ошибка форматирования Markdown, пробую отправить как обычный текст")
                    # Убираем все Markdown символы для обычного текста
                    plain_text = re.sub(r'[*_`\[\]()]', '', text)
                    payload_no_md = {
                        "chat_id": chat_id,
                        "text": plain_text,
                        "disable_web_page_preview": True,
                    }
                    response_plain = await self._client.post(
                        self.API_TMPL.format(token=self._token, method="sendMessage"),
                        json=payload_no_md,
                    )
                    data_plain = response_plain.json()
                    if response_plain.status_code == 200 and data_plain.get("ok"):
                        logger.info("Сообщение отправлено без Markdown форматирования")
                        return
                    elif response_plain.status_code == 403:
                        raise PublishError(f"Бот не имеет прав на отправку в канал. Убедитесь, что бот добавлен как администратор. Ответ: {data_plain}")
                    raise PublishError(f"Ошибка форматирования Markdown и отправки без него: {error_msg}")
                
                last_error = error_msg
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Экспоненциальная задержка: 2, 4, 8 сек
                    logger.warning("Ошибка отправки (попытка %d/%d): %s. Повтор через %d сек", attempt, max_retries, error_msg, wait_time)
                    await asyncio.sleep(wait_time)
                    
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, httpx.HTTPError) as exc:
                last_error = f"Сетевая ошибка: {type(exc).__name__}: {exc}"
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning("Сетевая ошибка (попытка %d/%d): %s. Повтор через %d сек", attempt, max_retries, last_error, wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    last_error = exc
        
        raise PublishError(f"Не удалось отправить сообщение после {max_retries} попыток: {last_error}")


__all__ = ["ReportPublisher", "PublishError"]
