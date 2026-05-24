# Deploy Guide — Fly.io + Supabase + GitHub Actions

Полный путь от пустого аккаунта до работающего бота. Всё делается из браузера
плюс одна сессия в GitHub Codespaces (~15 минут).

---

## 0. Чек-лист аккаунтов

- [ ] [@BotFather](https://t.me/BotFather) — Telegram-бот
- [ ] [platform.openai.com](https://platform.openai.com) — API-ключ + минимум $5 на балансе
- [ ] [supabase.com](https://supabase.com) — бесплатная Postgres БД
- [ ] [fly.io](https://fly.io) — хостинг бота
- [ ] [github.com](https://github.com) — для auto-deploy (репо уже есть)

---

## 1. BotFather (2 мин)

1. В Telegram открой [@BotFather](https://t.me/BotFather)
2. `/newbot` → имя бота (например `My Planner`) → username (например `my_planner_42_bot`, должен заканчиваться на `bot`)
3. Скопируй токен `123456789:ABCdef...` — это **BOT_TOKEN**
4. Опционально: `/setcommands` → выбери своего бота → вставь:
   ```
   start - Начать
   today - План на сегодня
   tomorrow - План на завтра
   week - План на неделю
   upcoming - Ближайшие события
   cancel - Отменить черновик
   ```

---

## 2. OpenAI API-ключ (3 мин)

1. [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → **Create new secret key**
2. Имя: `planner-bot` → скопируй `sk-...` — это **OPENAI_API_KEY**
3. [platform.openai.com/account/billing](https://platform.openai.com/account/billing) → пополни баланс на $5-10 (хватит на месяцы)

---

## 3. Supabase (Postgres БД, 3 мин)

1. [supabase.com](https://supabase.com) → Sign in → **New project**
2. Имя `planner-db`, регион **Frankfurt** (близко к Fly), пароль БД сохрани
3. Дождись готовности (~1 мин)
4. **Settings → Database → Connection string → URI** — там что-то вида:
   ```
   postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
   Замени `[PASSWORD]` на пароль из шага 2. Это **DATABASE_URL**.
5. **Settings → Database → Connection pooling** убедись что используешь **Transaction mode** (порт 6543) — иначе asyncpg не будет работать корректно с pgbouncer.

---

## 4. Fly.io (5 мин)

1. [fly.io](https://fly.io) → Sign up → привяжи карту (для верификации, free tier остаётся бесплатным)
2. **Dashboard → Account → Access Tokens → Create token** → имя `github-deploy`, токен сохрани — это **FLY_API_TOKEN**

---

## 5. Создать Fly app (один раз, через GitHub Codespaces — 5 мин)

Поскольку `fly launch` требует CLI, делаем это один раз через Codespaces (полностью в браузере).

1. Открой свой репозиторий на GitHub
2. **Code → Codespaces → Create codespace on `claude/mobile-app-capabilities-JHjWI`**
3. Откроется VS Code в браузере с терминалом. Выполни:

   ```bash
   # Установка flyctl
   curl -L https://fly.io/install.sh | sh
   export PATH="$HOME/.fly/bin:$PATH"

   # Логин
   fly auth login   # откроется ссылка → авторизуйся в браузере

   # Создаём app (имя должно быть уникальным глобально на Fly)
   fly apps create my-planner-bot-xxxx   # подставь своё

   # Открой fly.toml и замени `app = "CHANGE-ME-planner-bot"` на своё имя
   sed -i 's/CHANGE-ME-planner-bot/my-planner-bot-xxxx/' fly.toml

   # Положи секреты в Fly
   fly secrets set \
     BOT_TOKEN="123:ABC..." \
     OPENAI_API_KEY="sk-..." \
     DATABASE_URL="postgresql://..." \
     --app my-planner-bot-xxxx

   # Первый деплой
   fly deploy --remote-only

   # Проверь логи
   fly logs --app my-planner-bot-xxxx
   ```

4. Закоммить изменённый `fly.toml`:
   ```bash
   git add fly.toml
   git commit -m "chore: set fly app name"
   git push
   ```

---

## 6. Настроить GitHub Actions auto-deploy (2 мин)

Чтобы все следующие изменения деплоились автоматически по `git push`:

1. На GitHub: **Settings → Secrets and variables → Actions → New repository secret**
2. Имя: `FLY_API_TOKEN`, значение: токен из шага 4.2
3. Готово — теперь `.github/workflows/deploy.yml` будет запускаться на каждый push в `main`

---

## 7. Тест в Telegram

1. Открой своего бота по username
2. `/start` → должен ответить приветствием
3. Напиши: `завтра в 14:00 встреча с тестом, напомни за 5 минут`
4. Бот должен ответить карточкой события
5. Через нужное время придёт напоминание

Если что-то не работает:
```bash
fly logs --app my-planner-bot-xxxx
```

---

## Возможные проблемы

| Симптом | Причина | Решение |
|---|---|---|
| Бот не отвечает | Машина уснула | `fly machines start --app ...` |
| `connection refused` к БД | Неправильный pooling mode | В Supabase используй порт **6543** (Transaction mode) |
| Whisper падает на больших аудио | Аудио >25 MB | Не наша проблема — Telegram voice <1 MB |
| `BOT_TOKEN invalid` | Опечатка в секрете | `fly secrets list` и переустанови |
| OpenAI 401 | Кончился баланс / неверный ключ | Проверь в [platform.openai.com](https://platform.openai.com/usage) |

---

## Стоимость в месяц

- Fly.io: free tier (1 shared-cpu, 256 MB) — **$0**
- Supabase: free tier (500 MB, 50K MAU) — **$0**
- OpenAI: ~$1-2 при 50 сообщениях/день — **~$1-2**
- Telegram: всегда бесплатно

**Итого ~$1-2/мес** для одного активного пользователя.

---

## Дальнейшие изменения кода

После первого деплоя цикл такой:
1. Внеси изменения в код
2. Открой PR в `main` → CI прогонит `ruff + mypy + pytest`
3. Merge в `main` → GitHub Actions автодеплоит на Fly
4. `fly logs` чтобы увидеть как стартует

Чтобы откатить:
```bash
fly releases --app my-planner-bot-xxxx
fly deploy --image registry.fly.io/my-planner-bot-xxxx:deployment-XXX
```
