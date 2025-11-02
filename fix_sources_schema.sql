-- Fix sources table schema to match actual SQLite schema
ALTER TABLE sources RENAME TO sources_old;

CREATE TABLE sources (
    source_id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    source_type TEXT,
    hash TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
