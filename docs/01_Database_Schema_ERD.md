# TÀI LIỆU 1: DATABASE SCHEMA + ERD
## J.A.R.V.I.S Personal AI Assistant — MVP 1

**Phiên bản:** 1.0
**Ngày:** 18/05/2026
**DBMS:** PostgreSQL 15+ (bật extension `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector`)

---

## 1. NGUYÊN TẮC THIẾT KẾ

1. **UUID làm primary key** thay vì serial → tránh leak thông tin số lượng, dễ shard sau này.
2. **Timestamp đều là `TIMESTAMPTZ`** (UTC), application layer convert sang timezone user khi hiển thị.
3. **Soft-delete chuẩn** cho memory/conversation/todo/note bằng cột `deleted_at TIMESTAMPTZ NULL` (NULL = active).
4. **`created_at` / `updated_at`** có ở mọi bảng; `updated_at` được auto-update bằng trigger.
5. **Foreign key luôn `ON DELETE CASCADE`** khi quan hệ sở hữu mạnh (user → conversation → message).
6. **Index trên mọi FK và mọi cột thường xuyên filter** (status, deleted_at, due_at, user_id).
7. **JSONB cho metadata** (linh hoạt nhưng phải tránh dùng để lưu trường truy vấn nhiều).
8. **pgvector** cho memory embedding (1536-dim cho OpenAI `text-embedding-3-small`).

---

## 2. ERD (Mô tả quan hệ)

```
┌─────────┐
│ users   │
└────┬────┘
     │ 1:N
     ├─────────────┬──────────────┬───────────┬───────────┬───────────┬────────────┬──────────────┐
     ▼             ▼              ▼           ▼           ▼           ▼            ▼              ▼
┌────────────┐ ┌─────────┐  ┌────────┐  ┌────────┐  ┌─────────────┐ ┌──────────┐ ┌─────────────────┐
│conversations│ │ todos   │  │ notes  │  │reminders│  │  memories   │ │notifications│ │tool_execution  │
└────┬────────┘ └─────────┘  └────────┘  └────────┘  └─────────────┘ └──────────┘ │   _logs         │
     │ 1:N                                                                          └─────────────────┘
     ▼
┌──────────┐
│ messages │
└──────────┘
```

**Quan hệ chính:**
- `users 1—N conversations 1—N messages` (lưu hội thoại).
- `users 1—N {todos, notes, reminders, memories, notifications, tool_execution_logs}` (mọi bảng dữ liệu đều thuộc về 1 user).
- `notifications.related_entity_id` (UUID + `related_entity_type`) polymorphic ref tới todo/reminder.
- `tool_execution_logs.message_id` (NULL-able) liên kết tới message khởi nguồn (để debug).

---

## 3. EXTENSIONS & TRIGGER CHUNG

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- search ILIKE nhanh
CREATE EXTENSION IF NOT EXISTS "vector";    -- pgvector cho memory embedding

-- Trigger function chuẩn cho updated_at
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 4. CHI TIẾT TỪNG BẢNG

### 4.1 `users`

```sql
CREATE TABLE users (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255)    NOT NULL UNIQUE,
    password_hash   VARCHAR(255),                       -- NULL nếu login Google
    google_sub      VARCHAR(255)    UNIQUE,             -- Google OAuth subject
    name            VARCHAR(100)    NOT NULL,
    avatar_url      TEXT,
    timezone        VARCHAR(64)     NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    locale          VARCHAR(10)     NOT NULL DEFAULT 'vi-VN',
    assistant_name  VARCHAR(50)     NOT NULL DEFAULT 'JARVIS',
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_auth CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
);

CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.2 `conversations`

```sql
CREATE TABLE conversations (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255)    NOT NULL DEFAULT 'Cuộc hội thoại mới',
    last_message_at TIMESTAMPTZ,
    message_count   INTEGER         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ                                  -- soft delete
);

CREATE INDEX idx_conv_user_active ON conversations(user_id, last_message_at DESC)
    WHERE deleted_at IS NULL;
CREATE TRIGGER trg_conv_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.3 `messages`

```sql
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'tool');

CREATE TABLE messages (
    id                UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id   UUID            NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id           UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role              message_role    NOT NULL,
    content           TEXT            NOT NULL,
    metadata          JSONB           NOT NULL DEFAULT '{}'::jsonb,
    -- metadata example: {"tool_calls": [...], "model": "gpt-4o-mini", "tokens": {"in": 500, "out": 120}}
    tokens_in         INTEGER         NOT NULL DEFAULT 0,
    tokens_out        INTEGER         NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_msg_conv_created ON messages(conversation_id, created_at);
CREATE INDEX idx_msg_user_created ON messages(user_id, created_at DESC);
```

### 4.4 `todos`

```sql
CREATE TYPE todo_status   AS ENUM ('pending', 'in_progress', 'completed', 'cancelled');
CREATE TYPE todo_priority AS ENUM ('low', 'medium', 'high', 'urgent');

CREATE TABLE todos (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(500)    NOT NULL,
    description     TEXT,
    status          todo_status     NOT NULL DEFAULT 'pending',
    priority        todo_priority   NOT NULL DEFAULT 'medium',
    due_at          TIMESTAMPTZ,                                 -- NULL = no deadline
    completed_at    TIMESTAMPTZ,
    tags            TEXT[]          NOT NULL DEFAULT '{}',
    source          VARCHAR(20)     NOT NULL DEFAULT 'ui',       -- 'ui' | 'chat'
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_todo_user_status   ON todos(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_todo_user_due      ON todos(user_id, due_at) WHERE deleted_at IS NULL AND status != 'completed';
CREATE INDEX idx_todo_title_trgm    ON todos USING gin (title gin_trgm_ops);
CREATE TRIGGER trg_todo_updated_at BEFORE UPDATE ON todos
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.5 `notes`

```sql
CREATE TABLE notes (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(255)    NOT NULL,
    content         TEXT            NOT NULL DEFAULT '',
    tags            TEXT[]          NOT NULL DEFAULT '{}',
    source          VARCHAR(20)     NOT NULL DEFAULT 'ui',
    pinned          BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_note_user_pinned   ON notes(user_id, pinned DESC, updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_note_content_trgm  ON notes USING gin ((title || ' ' || content) gin_trgm_ops);
CREATE INDEX idx_note_tags          ON notes USING gin (tags);
CREATE TRIGGER trg_note_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.6 `reminders`

```sql
CREATE TYPE reminder_status AS ENUM ('scheduled', 'sent', 'cancelled', 'failed');

CREATE TABLE reminders (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(500)    NOT NULL,
    description     TEXT,
    remind_at       TIMESTAMPTZ     NOT NULL,                   -- BẮT BUỘC
    status          reminder_status NOT NULL DEFAULT 'scheduled',
    sent_at         TIMESTAMPTZ,
    retry_count     INTEGER         NOT NULL DEFAULT 0,
    last_error      TEXT,
    source          VARCHAR(20)     NOT NULL DEFAULT 'ui',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Index quan trọng cho scheduler: pick up reminder sắp tới hạn
CREATE INDEX idx_reminder_due       ON reminders(remind_at)
    WHERE status = 'scheduled' AND deleted_at IS NULL;
CREATE INDEX idx_reminder_user      ON reminders(user_id, remind_at DESC)
    WHERE deleted_at IS NULL;
CREATE TRIGGER trg_reminder_updated_at BEFORE UPDATE ON reminders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.7 `memories`

```sql
CREATE TYPE memory_type AS ENUM (
    'fact',         -- "tôi sinh ngày 1/1/1990"
    'preference',   -- "tôi thích cà phê đen không đường"
    'rule',         -- "không đặt lịch sau 22h"
    'relation',     -- "vợ tôi tên Lan"
    'goal',         -- "muốn học tiếng Nhật trong năm nay"
    'other'
);

CREATE TABLE memories (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type     memory_type     NOT NULL DEFAULT 'fact',
    content         TEXT            NOT NULL,
    importance      SMALLINT        NOT NULL DEFAULT 5,         -- 1-10
    embedding       VECTOR(1536),                                -- OpenAI text-embedding-3-small
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    use_count       INTEGER         NOT NULL DEFAULT 0,
    source_message_id UUID          REFERENCES messages(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    CONSTRAINT chk_importance CHECK (importance BETWEEN 1 AND 10)
);

CREATE INDEX idx_memory_user_active     ON memories(user_id, is_active, importance DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_memory_user_type       ON memories(user_id, memory_type)
    WHERE deleted_at IS NULL AND is_active = TRUE;
-- Vector index cho semantic search (ivfflat hoặc hnsw)
CREATE INDEX idx_memory_embedding       ON memories
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE TRIGGER trg_memory_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### 4.8 `tool_execution_logs`

```sql
CREATE TYPE tool_status AS ENUM ('success', 'failed', 'timeout');

CREATE TABLE tool_execution_logs (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id      UUID            REFERENCES messages(id) ON DELETE SET NULL,
    tool_name       VARCHAR(64)     NOT NULL,
    input           JSONB           NOT NULL,
    output          JSONB,
    status          tool_status     NOT NULL,
    error_message   TEXT,
    duration_ms     INTEGER         NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_log_user_time     ON tool_execution_logs(user_id, created_at DESC);
CREATE INDEX idx_tool_log_tool_status   ON tool_execution_logs(tool_name, status, created_at DESC);
```

### 4.9 `notifications`

```sql
CREATE TYPE notification_type   AS ENUM ('reminder', 'system', 'todo_overdue');
CREATE TYPE notification_status AS ENUM ('pending', 'delivered', 'read', 'dismissed');

CREATE TABLE notifications (
    id                  UUID                PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID                NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                notification_type   NOT NULL,
    title               VARCHAR(255)        NOT NULL,
    body                TEXT,
    status              notification_status NOT NULL DEFAULT 'pending',
    related_entity_type VARCHAR(32),                       -- 'reminder' | 'todo' | NULL
    related_entity_id   UUID,                              -- polymorphic
    delivered_at        TIMESTAMPTZ,
    read_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notif_user_status      ON notifications(user_id, status, created_at DESC);
CREATE INDEX idx_notif_user_unread      ON notifications(user_id, created_at DESC)
    WHERE status IN ('pending', 'delivered');
```

### 4.10 `auth_sessions` (bổ sung)

```sql
CREATE TABLE auth_sessions (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
    user_agent      TEXT,
    ip_address      INET,
    expires_at      TIMESTAMPTZ     NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_session_user_active ON auth_sessions(user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_session_token       ON auth_sessions(refresh_token_hash);
```

---

## 5. SEED DATA (DEV ONLY)

```sql
INSERT INTO users (id, email, password_hash, name, timezone)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'demo@jarvis.local',
    crypt('demo1234', gen_salt('bf')),
    'Demo User',
    'Asia/Ho_Chi_Minh'
);
```

---

## 6. MIGRATION STRATEGY

- Sử dụng **Alembic** (nếu chọn FastAPI) hoặc **Prisma Migrate** (nếu Next.js).
- Đặt tên migration: `YYYYMMDDHHMM_action.sql`, ví dụ `202605181000_init_schema.sql`.
- Mỗi migration **có cả `up` và `down`**.
- Không bao giờ chỉnh sửa migration đã chạy production — luôn tạo migration mới.

---

## 7. BACKUP & RETENTION

| Mục | Chính sách |
|-----|-----------|
| Full backup | Hàng ngày 03:00 UTC, giữ 30 ngày |
| WAL archiving | Liên tục, giữ 7 ngày → point-in-time recovery |
| Soft-delete cleanup | Xóa cứng record `deleted_at < NOW() - INTERVAL '90 days'` (chạy hàng tuần) |
| Tool log retention | Xóa cứng record cũ hơn 90 ngày |
| Notification cũ | Xóa cứng `status='read'` hoặc `dismissed` cũ hơn 30 ngày |

---

## 8. NHỮNG CÂU TRUY VẤN QUAN TRỌNG (Reference)

### Lấy dashboard today
```sql
-- Todos hôm nay
SELECT * FROM todos
WHERE user_id = $1
  AND deleted_at IS NULL
  AND status != 'completed'
  AND (due_at::date = (NOW() AT TIME ZONE $2)::date OR due_at IS NULL)
ORDER BY priority DESC, due_at ASC;

-- Reminders hôm nay
SELECT * FROM reminders
WHERE user_id = $1
  AND deleted_at IS NULL
  AND status = 'scheduled'
  AND remind_at::date = (NOW() AT TIME ZONE $2)::date
ORDER BY remind_at;

-- Todos quá hạn
SELECT * FROM todos
WHERE user_id = $1
  AND deleted_at IS NULL
  AND status NOT IN ('completed', 'cancelled')
  AND due_at < NOW()
ORDER BY due_at;
```

### Semantic memory search
```sql
SELECT id, content, memory_type, importance,
       1 - (embedding <=> $1::vector) AS similarity
FROM memories
WHERE user_id = $2
  AND is_active = TRUE
  AND deleted_at IS NULL
  AND 1 - (embedding <=> $1::vector) > 0.7
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

### Scheduler pick reminder (mỗi 60s)
```sql
UPDATE reminders
SET status = 'sent', sent_at = NOW()
WHERE id IN (
    SELECT id FROM reminders
    WHERE status = 'scheduled'
      AND remind_at <= NOW()
      AND deleted_at IS NULL
    FOR UPDATE SKIP LOCKED
    LIMIT 100
)
RETURNING *;
```

---

## 9. KÍCH THƯỚC ƯỚC LƯỢNG (1 user, 1 năm)

| Bảng | Ước lượng số dòng | Dung lượng |
|------|------------------|------------|
| messages | ~50,000 (150/ngày) | ~50 MB |
| memories | ~500 | ~5 MB (kèm vector) |
| todos | ~1,500 | ~1 MB |
| notes | ~500 | ~2 MB |
| reminders | ~1,000 | ~0.5 MB |
| tool_execution_logs | ~30,000 | ~30 MB |
| **Tổng/user/năm** | | **~90 MB** |

→ Postgres Free Tier (Supabase/Neon: 500 MB) đủ cho ~5 user trong 1 năm.
