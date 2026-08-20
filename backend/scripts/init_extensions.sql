-- Enabled at container init. pgvector is unused until Phase 3, but installing it now
-- means Phase 3 adds a column rather than rebuilding the database container.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
