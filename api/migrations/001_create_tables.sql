-- Jarvis v2 Database Schema
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New Query)
-- URL: https://supabase.com/dashboard/project/ztybsqnvncualuovrimt/sql/new

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    auto_title TEXT DEFAULT '',
    custom_name TEXT DEFAULT '',
    message_count INTEGER DEFAULT 0,
    pinned BOOLEAN DEFAULT false,
    model TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    last_active TIMESTAMPTZ DEFAULT now()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    prefix TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT DEFAULT '',
    action TEXT NOT NULL,
    ip TEXT DEFAULT '',
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Usage tracking table (aggregated per user per day)
CREATE TABLE IF NOT EXISTS usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    requests INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    date DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_id, date)
);

-- Settings table (per-user settings override)
CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT UNIQUE NOT NULL,
    backend TEXT DEFAULT '',
    model TEXT DEFAULT '',
    max_tokens INTEGER DEFAULT 4096,
    system_prompt TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- SECONDARY TABLES
-- ============================================================

-- Webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    url TEXT NOT NULL,
    events JSONB DEFAULT '[]',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_fired TIMESTAMPTZ,
    fire_count INTEGER DEFAULT 0,
    last_error TEXT DEFAULT ''
);

-- Scheduled tasks table
CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    cron TEXT NOT NULL,
    task_type TEXT NOT NULL CHECK (task_type IN ('shell', 'conversation', 'tool')),
    payload JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_run TIMESTAMPTZ,
    last_status TEXT,
    last_error TEXT,
    run_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0
);

-- Shared conversations table
CREATE TABLE IF NOT EXISTS shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT DEFAULT '',
    title TEXT DEFAULT '',
    messages JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    view_count INTEGER DEFAULT 0
);

-- User prompt templates table
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'custom',
    prompt TEXT NOT NULL,
    icon TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_user_id ON webhooks(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_shares_user_id ON shares(user_id);
CREATE INDEX IF NOT EXISTS idx_shares_share_id ON shares(share_id);
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON templates(user_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Allow anon key full access (backend handles auth via JWT)
-- Our FastAPI backend is the only consumer of these tables.
CREATE POLICY "Backend full access" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON api_keys FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON usage FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON settings FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON audit_log FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON webhooks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON schedules FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON shares FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Backend full access" ON templates FOR ALL USING (true) WITH CHECK (true);
