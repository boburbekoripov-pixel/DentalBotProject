-- Telegram Planner Bot initial schema.

CREATE TABLE IF NOT EXISTS users (
    id            BIGINT PRIMARY KEY,
    username      TEXT,
    first_name    TEXT,
    timezone      TEXT NOT NULL DEFAULT 'Asia/Tashkent',
    language      TEXT NOT NULL DEFAULT 'ru',
    daily_digest  BOOLEAN NOT NULL DEFAULT TRUE,
    digest_hour   SMALLINT NOT NULL DEFAULT 8,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    start_at      TIMESTAMPTZ NOT NULL,
    end_at        TIMESTAMPTZ,
    location      TEXT,
    notes         TEXT,
    participants  TEXT[] NOT NULL DEFAULT '{}',
    recurrence    JSONB,
    source        TEXT NOT NULL DEFAULT 'telegram',
    gcal_event_id TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_user_start ON events(user_id, start_at);

CREATE TABLE IF NOT EXISTS reminders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id     UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL,
    fire_at      TIMESTAMPTZ NOT NULL,
    offset_min   INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    sent_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT reminders_status_check CHECK (status IN ('pending', 'sent', 'failed', 'cancelled'))
);
CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(fire_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_reminders_event ON reminders(event_id);

-- Per-user draft event waiting for clarification (only one in flight at a time).
CREATE TABLE IF NOT EXISTS pending_events (
    user_id     BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    draft       JSONB NOT NULL,
    question    TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversation log used as short-term context window for the LLM.
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT conversations_role_check CHECK (role IN ('user', 'assistant', 'system'))
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_time ON conversations(user_id, created_at DESC);
