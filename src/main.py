"""Основная точка запуска недельного Telegram-дайджеста."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Tuple

from telethon import TelegramClient
from telethon import utils as tl_utils

from .collector import CollectedMessage, fetch_channel_messages, iterate_channels
from .config import ConfigError, load_config
from .processing import build_overview_request, build_summary_request
from .publisher import PublishError, ReportPublisher
from .summarizer import DeepSeekSummarizer, SummaryRequest, SummarizationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def gather_channel_summaries(
    client: TelegramClient,
    summarizer: DeepSeekSummarizer,
    channels: List[str],
    days_back: int,
) -> List[Tuple[str, str]]:
    """Собирает сообщения по каждому каналу и формирует их текстовые выжимки."""

    summaries: list[Tuple[str, str]] = []

    for channel_spec in channels:
        logger.info("Собираю сообщения канала %s", channel_spec)

        try:
            entity = await client.get_entity(channel_spec)
        except Exception as exc:
            logger.error("Не удалось получить данные канала %s: %s", channel_spec, exc)
            continue

        channel_label = tl_utils.get_display_name(entity) or getattr(entity, "username", None) or channel_spec

        messages: List[CollectedMessage] = await fetch_channel_messages(
            client, entity, channel_label, days_back
        )
        logger.info("Получено %d подходящих сообщений", len(messages))

        request: SummaryRequest = build_summary_request(channel_label, messages)
        summary_text = (await summarizer.summarize([request]))[0]

        summaries.append((channel_label, summary_text))

    return summaries


def split_for_telegram(text: str, max_len: int = 3900) -> List[str]:
    """Делит текст на части, укладывающиеся в лимит Telegram.

    Учитываем запас на Markdown-символы и переносы. Сначала пробуем резать по абзацам,
    при необходимости — по символам.
    """

    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    paragraphs = text.split("\n\n")
    buffer = ""

    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip()
        if not buffer:
            candidate = paragraph

        if len(candidate) <= max_len:
            buffer = candidate
            continue

        if buffer:
            chunks.append(buffer)
            buffer = ""

        if len(paragraph) <= max_len:
            buffer = paragraph
            continue

        # Абзац всё равно слишком длинный — режем по символам.
        start = 0
        while start < len(paragraph):
            end = min(start + max_len, len(paragraph))
            chunks.append(paragraph[start:end])
            start = end

    if buffer:
        chunks.append(buffer)

    return chunks


async def main() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("Ошибка конфигурации: %s", exc)
        raise SystemExit(1) from exc

    with config.channels_file.open("r", encoding="utf-8") as fh:
        channels = list(iterate_channels(fh))

    if not channels:
        logger.error("Список каналов пуст. Заполните файл %s", config.channels_file)
        raise SystemExit(2)

    logger.info("Будут обработаны каналы: %s", ", ".join(channels))

    client = TelegramClient(
        config.telegram.session_name,
        config.telegram.api_id,
        config.telegram.api_hash,
    )
    start_kwargs: dict[str, str] = {}
    if config.telegram.phone:
        start_kwargs["phone"] = config.telegram.phone

    summarizer = DeepSeekSummarizer(
        api_key=config.deepseek.api_key,
        model=config.deepseek.model,
        language=config.deepseek.summary_language,
    )
    publisher = ReportPublisher(config.telegram.bot_token)

    try:
        await client.start(**start_kwargs)
        async with client:
            channel_summaries = await gather_channel_summaries(
                client, summarizer, channels, config.days_back
            )

        overall_request = build_overview_request([summary for _, summary in channel_summaries])
        overall_summary = (await summarizer.summarize([overall_request]))[0]

        overall_message = "*Недельный дайджест — общий обзор*\n\n" + overall_summary
        for chunk in split_for_telegram(overall_message):
            await publisher.send_markdown(config.telegram.report_channel_id, chunk)

        for channel_label, summary in channel_summaries:
            message_text = f"*{channel_label}*\n{summary}"
            for chunk in split_for_telegram(message_text):
                await publisher.send_markdown(config.telegram.report_channel_id, chunk)

        logger.info("Отчёт успешно отправлен")

    except SummarizationError as exc:
        logger.error("Ошибка при обращении к DeepSeek: %s", exc)
        raise SystemExit(3) from exc
    except PublishError as exc:
        logger.error("Ошибка при отправке отчёта: %s", exc)
        raise SystemExit(4) from exc
    finally:
        await summarizer.close()
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
