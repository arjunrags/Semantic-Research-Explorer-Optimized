-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Full-text search index will be created by SQLAlchemy migration.
-- This script ensures extensions exist before alembic runs.
