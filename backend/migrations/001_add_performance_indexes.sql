-- Performance indexes for Chanda Tracker (run in Supabase SQL editor).
-- Postgres does NOT auto-index foreign keys, and UNIQUE constraints only index
-- users.email / users.roll_no themselves. Apply once to an existing database.

-- payments: dashboards filter/aggregate by these constantly
CREATE INDEX IF NOT EXISTS idx_payments_giver_id ON payments (giver_id);
CREATE INDEX IF NOT EXISTS idx_payments_collector_id ON payments (collector_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status);

-- otp_codes: every verify-otp / reset-password lookup filters by email
CREATE INDEX IF NOT EXISTS idx_otp_codes_email ON otp_codes (email);

-- broadcasts: feed query filters by role/year/branch/gender
CREATE INDEX IF NOT EXISTS idx_broadcasts_filter_role ON broadcasts (filter_role);
CREATE INDEX IF NOT EXISTS idx_broadcasts_filter_year ON broadcasts (filter_year);
CREATE INDEX IF NOT EXISTS idx_broadcasts_filter_branch ON broadcasts (filter_branch);
CREATE INDEX IF NOT EXISTS idx_broadcasts_filter_gender ON broadcasts (filter_gender);

-- users.email and users.roll_no already have UNIQUE indexes auto-created by Postgres:
-- SELECT indexname FROM pg_indexes WHERE tablename = 'users';
