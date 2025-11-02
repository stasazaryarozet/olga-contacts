-- PostgreSQL Schema for Supabase
-- Converted from SQLite schema in enhanced_graph_db.py
-- Date: 2025-11-01

-- ============================================================
-- GRAPH ZONE: Fast, clean, query-ready
-- ============================================================

-- Entities (canonical) - Enhanced schema for business contacts
CREATE TABLE IF NOT EXISTS entities (
    entity_id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT NOT NULL,
    primary_identifier TEXT,
    status TEXT DEFAULT 'unknown',
    domain TEXT,
    relationship_strength REAL,
    first_seen TEXT,
    last_interaction TEXT,
    notes TEXT,
    tags TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Identifiers (many-to-one with entities)
CREATE TABLE IF NOT EXISTS identifiers (
    identifier TEXT PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    identifier_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

-- Edges (relations between entities)
CREATE TABLE IF NOT EXISTS edges (
    edge_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL,
    object_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,
    event_date TEXT,
    confidence REAL DEFAULT 1.0,
    source_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES entities(entity_id),
    FOREIGN KEY (object_id) REFERENCES entities(entity_id),
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- ============================================================
-- CONTEXT ZONE: Rich, provenance-heavy
-- ============================================================

-- Sources (where did the fact come from?)
CREATE TABLE IF NOT EXISTS sources (
    source_id SERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_uri TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

-- Raw Data (original content for each source)
CREATE TABLE IF NOT EXISTS raw_data (
    raw_id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Graph Zone indexes
CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges(subject_id);
CREATE INDEX IF NOT EXISTS idx_edges_object ON edges(object_id);
CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id);

-- Business contacts indexes
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain);
CREATE INDEX IF NOT EXISTS idx_entities_strength ON entities(relationship_strength);
CREATE INDEX IF NOT EXISTS idx_entities_last_interaction ON entities(last_interaction);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);

-- Context Zone indexes
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_data_source ON raw_data(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_data_hash ON raw_data(content_hash);

