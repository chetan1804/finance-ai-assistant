ALTER TABLE user_credentials
    ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0;

ALTER TABLE user_credentials
    ADD COLUMN locked_until TIMESTAMPTZ;

ALTER TABLE user_credentials
    ADD COLUMN last_login_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
    ON auth_sessions(user_id, revoked_at, refresh_expires_at);
