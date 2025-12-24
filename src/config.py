"""Конфигурация приложения.

Загружает параметры из переменных окружения или файла .env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Считываем переменные сначала из .env (если есть), затем из окружения.
load_dotenv(ENV_PATH, override=False)
load_dotenv(override=False)


@dataclass(frozen=True)
class TelegramConfig:
    """Параметры доступа к Telegram API и каналам."""

    api_id: int
    api_hash: str
    phone: Optional[str]
    bot_token: str
    report_channel_id: str
    session_name: str = "telegram_summary_session"


@dataclass(frozen=True)
class DeepSeekConfig:
    """Параметры доступа к DeepSeek API."""

    api_key: str
    model: str
    summary_language: str


@dataclass(frozen=True)
class AppConfig:
    """Корневая структура конфигурации приложения."""

    telegram: TelegramConfig
    deepseek: DeepSeekConfig
    channels_file: Path
    days_back: int = 7


class ConfigError(RuntimeError):
    """Ошибка, возникающая при отсутствии обязательных параметров."""


def _require(name: str) -> str:
    """Возвращает значение переменной окружения или поднимает исключение."""

    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Не задана переменная окружения {name}")
    return value


def load_config() -> AppConfig:
    """Читает конфигурацию из окружения и формирует объект AppConfig."""

    telegram_config = TelegramConfig(
        api_id=int(_require("TELEGRAM_API_ID")),
        api_hash=_require("TELEGRAM_API_HASH"),
        phone=os.getenv("TELEGRAM_PHONE"),
        bot_token=_require("TELEGRAM_BOT_TOKEN"),
        report_channel_id=_require("REPORT_CHANNEL_ID"),
        session_name=os.getenv("TELEGRAM_SESSION_NAME", "telegram_summary_session"),
    )

    deepseek_config = DeepSeekConfig(
        api_key=_require("DEEPSEEK_API_KEY"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        summary_language=os.getenv("SUMMARY_LANGUAGE", "ru"),
    )

    channels_file = Path(os.getenv("CHANNELS_FILE", BASE_DIR / "channels.txt"))

    if not channels_file.exists():
        raise ConfigError(
            "Файл со списком каналов не найден. Убедитесь, что CHANNELS_FILE указывает на корректный путь."
        )

    days_back = int(os.getenv("DAYS_BACK", "7"))

    return AppConfig(
        telegram=telegram_config,
        deepseek=deepseek_config,
        channels_file=channels_file,
        days_back=days_back,
    )


__all__ = ["AppConfig", "TelegramConfig", "DeepSeekConfig", "ConfigError", "load_config"]
