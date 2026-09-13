-- Google authentication support for Chanda Tracker (run in Supabase SQL editor).
-- Adds google_sub column to users and makes password_hash nullable for Google-only accounts.

ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255) UNIQUE;
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Ensure every user has at least one authentication method (password or Google).
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_method_check;
ALTER TABLE users ADD CONSTRAINT users_auth_method_check
  CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL);

-- Partial index for fast google_sub lookups (skips NULLs).
CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users (google_sub) WHERE google_sub IS NOT NULL;
