# Telegram News Summary

Инструмент формирует недельный дайджест по выбранным Telegram-каналам: собирает сообщения за последние 7 дней, отправляет их в DeepSeek для получения краткого саммари и публикует отчёт в выделенный канал.

## Возможности
- асинхронный сбор сообщений из публичных каналов через Telethon;
- отбор наиболее значимых постов (по просмотрам/дате) и подготовка текста для модели;
- обращение к API DeepSeek (chat completions) для генерации русскоязычного отчёта;
- отправка итогового Markdown-сообщения в канал через Telegram Bot API;
- конфигурация через `.env` и `channels.txt`, что позволяет менять источники без правки кода.

## Структура проекта
```
├── channels.txt          # список каналов для мониторинга
├── requirements.txt      # зависимости Python
├── .env.example          # шаблон переменных окружения
└── src
    ├── __init__.py
    ├── collector.py
    ├── config.py
    ├── main.py
    ├── processing.py
    ├── publisher.py
    └── summarizer.py
```

## Подготовка окружения
1. Установите Python 3.10+ и создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   # source .venv/bin/activate      # Linux/macOS
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

## Настройка переменных окружения
Заполните файл `.env` на основе `.env.example`:
```
TELEGRAM_API_ID=ваш_api_id
TELEGRAM_API_HASH=ваш_api_hash
TELEGRAM_PHONE=+71234567890           # номер, который проходит авторизацию в Telethon (опционально)
TELEGRAM_SESSION_NAME=telegram_summary_session  # имя файла сессии (можно оставить по умолчанию)
TELEGRAM_BOT_TOKEN=ваш_bot_token
REPORT_CHANNEL_ID=@summary_channel     # username или numeric ID канала для отчёта
DEEPSEEK_API_KEY=ваш_deepseek_key
DEEPSEEK_MODEL=deepseek-chat           # можно изменить при необходимости
SUMMARY_LANGUAGE=ru                    # язык итогового текста
CHANNELS_FILE=channels.txt             # путь к файлу со списком каналов
DAYS_BACK=7                            # глубина истории в днях
```
> ⚠️ Не храните реальные ключи в репозитории — добавьте `.env` в `.gitignore`.

### Авторизация Telethon
При первом запуске Telethon попросит код подтверждения и, возможно, пароль 2FA. Сессия будет сохранена в файл с именем из `TELEGRAM_SESSION_NAME` (по умолчанию `telegram_summary_session.session`) рядом с проектом.

**Важно:** Если вы меняете аккаунт Telegram (новые `TELEGRAM_API_ID`/`TELEGRAM_API_HASH`/`TELEGRAM_PHONE`), нужно либо:
- Удалить старый файл сессии (например, `telegram_summary_session.session`)
- Или указать новое имя сессии через переменную `TELEGRAM_SESSION_NAME` в `.env`

## Список каналов
- Откройте `channels.txt` и добавьте по одному каналу в строке (можно использовать `@username` или полную ссылку `https://t.me/...`).
- Строки, начинающиеся с `#`, считаются комментариями.

## Запуск
Выполните:
```bash
python -m src.main
```
Скрипт соберёт сообщения, запросит саммари у DeepSeek и отправит отчёт в канал несколькими сообщениями: общий обзор и отдельные блоки по каждому источнику (если текст длинный, он автоматически разбивается на части).

### Настройка расписания (cron)
Пример записи для запуска каждое воскресенье в 12:00 (UTC) на Linux:
```cron
0 12 * * 0 /usr/bin/env bash -c 'cd /path/to/Telegram-news-summary && source .venv/bin/activate && python -m src.main'
```
Убедитесь, что учли временную зону сервера и корректные пути. На Windows можно использовать Планировщик заданий.

## Дополнительные советы
- Следите за лимитами DeepSeek (50–100k токенов/сутки). При большом количестве каналов уменьшайте `DEFAULT_TOP_MESSAGES` в `processing.py`.
- Для диагностики используйте логи уровня `INFO`, которые выводятся в STDOUT.
- При сбое обращения к DeepSeek или Bot API скрипт завершится с ненулевым кодом и сообщением об ошибке.

## TODO
- Добавить юнит-тесты для обработки текста.
- Реализовать кэширование промежуточных саммари при повторных запусках.
