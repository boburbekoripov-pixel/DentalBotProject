# Telegram AI Planner Bot

Персональный AI-планировщик в Telegram. Принимает текст и голос,
понимает естественный язык (русский / узбекский / английский), сохраняет
события, шлёт напоминания в точное время и присылает план дня по утрам.

## Возможности

- 📝 Текст и голос (Whisper)
- 🧠 NLU через GPT-4o-mini (структурированный JSON)
- 🔁 Recurring events (daily / weekly / monthly / yearly)
- ⏰ Точные напоминания через APScheduler с восстановлением после перезапуска
- ☀️ Daily digest в нужный час по локальному времени пользователя
- 🗑 Inline-кнопки удаления, multi-turn уточнения при недостающих данных
- 🌐 Поддержка нескольких пользователей с разными часовыми поясами

## Стек

- Python 3.11+
- aiogram 3.x (Telegram Bot API)
- OpenAI Python SDK (GPT + Whisper)
- PostgreSQL + asyncpg
- APScheduler (in-process scheduler)
- Pydantic v2

## Быстрый старт (Docker)

```bash
cp .env.example .env
# заполни BOT_TOKEN и OPENAI_API_KEY
docker compose up --build
```

Postgres поднимется автоматически, миграция применится при старте бота.

## Продакшн деплой

Полная пошаговая инструкция: **[DEPLOY.md](./DEPLOY.md)** —
Fly.io + Supabase + GitHub Actions auto-deploy, всё в браузере (~15 минут).

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Запусти Postgres любым удобным способом, затем:
export DATABASE_URL=postgresql://planner:planner@localhost:5432/planner
cp .env.example .env  # отредактируй
python -m bot.main
```

## Создание Telegram-бота

1. Открой [@BotFather](https://t.me/BotFather), команда `/newbot`
2. Скопируй токен в `BOT_TOKEN`
3. (Опционально) задай команды:
   ```
   /setcommands
   start - Начать
   today - План на сегодня
   tomorrow - План на завтра
   week - План на неделю
   upcoming - Ближайшие события
   cancel - Отменить текущий черновик
   ```

## Примеры использования

```
Пользователь: завтра в 9 встреча с Джахонгиром, напомни за 20 минут
Бот: 📌 Встреча с Джахонгиром
     🕐 24 мая, 09:00
     👥 Джахонгир
     ✓ Сохранил. Напоминания: 1

Пользователь: каждый понедельник в 19:00 тренировка
Бот: 📌 Тренировка
     🕐 25 мая, 19:00
     🔁 еженедельно

Пользователь: что у меня завтра?
Бот: Завтра в 09:00 — Встреча с Джахонгиром.

Пользователь: удали тренировку
Бот: Удалил: Тренировка
```

## Разработка

```bash
# линтер + типы + тесты
ruff check bot tests
ruff format --check bot tests
mypy bot
pytest -v
```

## Структура

```
bot/
├── main.py              # точка входа
├── config.py            # настройки из .env
├── db/
│   ├── client.py        # asyncpg pool + миграции
│   ├── schemas.py       # Pydantic-модели
│   └── repositories.py  # User/Event/Reminder/Pending/Conversation
├── services/
│   ├── nlu.py           # OpenAI extraction
│   ├── whisper.py       # voice → text
│   ├── reminders.py     # APScheduler
│   ├── digest.py        # ежедневная сводка
│   └── formatting.py    # карточки событий
├── handlers/
│   ├── commands.py      # /start /today /week ...
│   ├── text.py          # NLU pipeline для текста
│   ├── voice.py         # voice → Whisper → text pipeline
│   ├── callbacks.py     # inline-кнопки
│   └── deps.py          # DI-контейнер
└── utils/tz.py
migrations/001_init.sql
tests/                   # pure-logic тесты
```

## Roadmap

- [ ] Двусторонняя синхронизация с Google Calendar
- [ ] Семантическая память на pgvector (long-term context)
- [ ] Полный RRULE для сложной периодичности
- [ ] Snooze / "перенеси на час" inline-actions
- [ ] Goal / week-review режим (как Notion habits)

## Лицензия

MIT
