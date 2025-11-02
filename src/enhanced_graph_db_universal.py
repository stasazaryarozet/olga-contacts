"""
Enhanced Graph Database with PostgreSQL and SQLite support
Automatically detects connection type from environment
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Try PostgreSQL, fallback to SQLite
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

import sqlite3


class EnhancedGraphDB:
    """
    Enhanced graph database with:
    1. PostgreSQL (Supabase) support for production
    2. SQLite fallback for local development
    3. Canonical IDs (Entity Resolution)
    4. Graph Zone / Context Zone separation
    5. Unified fact gateway (add_fact)
    6. Export capabilities (GraphML, JSON)
    """
    
    def __init__(self, db_path=None, postgres_url=None):
        """
        Initialize database connection.
        
        Priority:
        1. postgres_url (if provided)
        2. DATABASE_URL env var (Streamlit secrets)
        3. db_path (SQLite fallback)
        """
        self.db_type = None
        self.conn = None
        
        # Try PostgreSQL first
        postgres_url = postgres_url or os.getenv('DATABASE_URL')
        
        if postgres_url and POSTGRES_AVAILABLE:
            try:
                self.conn = psycopg2.connect(postgres_url)
                self.db_type = 'postgresql'
                print("✅ Connected to PostgreSQL")
            except Exception as e:
                print(f"⚠️ PostgreSQL connection failed: {e}")
                print("   Falling back to SQLite...")
        
        # Fallback to SQLite
        if not self.conn:
            db_path = db_path or "data/contacts_v2.db"
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.db_type = 'sqlite'
            print(f"✅ Connected to SQLite: {db_path}")
        
        self._create_enhanced_schema()
    
    def _create_enhanced_schema(self):
        """Create enhanced database schema (PostgreSQL or SQLite)."""
        
        if self.db_type == 'postgresql':
            self._create_postgresql_schema()
        else:
            self._create_sqlite_schema()
    
    def _create_postgresql_schema(self):
        """Create PostgreSQL schema."""
        cursor = self.conn.cursor()
        
        # Entities
        cursor.execute("""
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
            )
        """)
        
        # Identifiers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS identifiers (
                identifier TEXT PRIMARY KEY,
                entity_id INTEGER NOT NULL,
                identifier_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            )
        """)
        
        # Edges
        cursor.execute("""
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
                FOREIGN KEY (object_id) REFERENCES entities(entity_id)
            )
        """)
        
        # Sources
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id SERIAL PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_uri TEXT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Raw Data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                raw_id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges(subject_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_object ON edges(object_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_strength ON entities(relationship_strength)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_last_interaction ON entities(last_interaction)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        
        self.conn.commit()
        cursor.close()
    
    def _create_sqlite_schema(self):
        """Create SQLite schema (existing implementation)."""
        # Entities
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Identifiers
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS identifiers (
                identifier TEXT PRIMARY KEY,
                entity_id INTEGER NOT NULL,
                identifier_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            )
        """)
        
        # Edges
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                object_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                event_date TEXT,
                confidence REAL DEFAULT 1.0,
                source_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES entities(entity_id),
                FOREIGN KEY (object_id) REFERENCES entities(entity_id)
            )
        """)
        
        # Sources
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_uri TEXT,
                ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Raw Data
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            )
        """)
        
        # Indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges(subject_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_object ON edges(object_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_strength ON entities(relationship_strength)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_last_interaction ON entities(last_interaction)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        
        self.conn.commit()
    
    def execute(self, query, params=None):
        """Execute query (abstraction for PostgreSQL/SQLite differences)."""
        cursor = self.conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor
    
    def fetchone(self, query, params=None):
        """Fetch one result."""
        cursor = self.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def fetchall(self, query, params=None):
        """Fetch all results."""
        cursor = self.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    
    def add_fact(self, subject_label: str, relation_type: str, object_label: str,
                 subject_type: str = "Person", object_type: str = "Person",
                 event_date: Optional[str] = None, confidence: float = 1.0,
                 source_type: str = "manual", source_uri: Optional[str] = None,
                 raw_content: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Unified gateway for adding facts to the graph.
        Handles entity resolution and provenance automatically.
        
        Returns: (subject_id, object_id, edge_id)
        """
        # Resolve or create subject
        subject_id = self._resolve_or_create_entity(subject_label, subject_type)
        
        # Resolve or create object
        object_id = self._resolve_or_create_entity(object_label, object_type)
        
        # Create source if not exists
        source_id = self._get_or_create_source(source_type, source_uri)
        
        # Store raw content if provided
        if raw_content:
            self._store_raw_data(source_id, raw_content)
        
        # Create edge
        edge_id = self._create_edge(subject_id, object_id, relation_type, 
                                    event_date, confidence, source_id)
        
        return (subject_id, object_id, edge_id)
    
    def _resolve_or_create_entity(self, label: str, entity_type: str) -> int:
        """Resolve or create entity (simplified entity resolution)."""
        # Check if entity exists
        result = self.fetchone(
            "SELECT entity_id FROM entities WHERE label = ? AND type = ?",
            (label, entity_type)
        )
        
        if result:
            return result[0]
        
        # Create new entity
        cursor = self.execute(
            """
            INSERT INTO entities (label, type, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (label, entity_type, datetime.now().isoformat(), datetime.now().isoformat())
        )
        
        entity_id = cursor.lastrowid
        self.conn.commit()
        cursor.close()
        
        # Add identifier
        self.execute(
            "INSERT OR IGNORE INTO identifiers (identifier, entity_id, identifier_type) VALUES (?, ?, ?)",
            (label.lower(), entity_id, 'canonical')
        )
        self.conn.commit()
        
        return entity_id
    
    def _get_or_create_source(self, source_type: str, source_uri: Optional[str]) -> int:
        """Get or create source."""
        if source_uri:
            result = self.fetchone(
                "SELECT source_id FROM sources WHERE source_uri = ?",
                (source_uri,)
            )
            if result:
                return result[0]
        
        cursor = self.execute(
            "INSERT INTO sources (source_type, source_uri, ingested_at) VALUES (?, ?, ?)",
            (source_type, source_uri, datetime.now().isoformat())
        )
        
        source_id = cursor.lastrowid
        self.conn.commit()
        cursor.close()
        
        return source_id
    
    def _store_raw_data(self, source_id: int, content: str):
        """Store raw data with hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        self.execute(
            """
            INSERT OR IGNORE INTO raw_data (source_id, content, content_hash, extracted_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, content, content_hash, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def _create_edge(self, subject_id: int, object_id: int, relation_type: str,
                    event_date: Optional[str], confidence: float, source_id: int) -> int:
        """Create edge."""
        cursor = self.execute(
            """
            INSERT INTO edges (subject_id, object_id, relation_type, event_date, confidence, source_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (subject_id, object_id, relation_type, event_date, confidence, source_id, datetime.now().isoformat())
        )
        
        edge_id = cursor.lastrowid
        self.conn.commit()
        cursor.close()
        
        return edge_id
    
    def export_graphml(self, output_path: str):
        """Export graph to GraphML format."""
        # Get all entities
        entities = self.fetchall("SELECT entity_id, label, type FROM entities")
        
        # Get all edges
        edges = self.fetchall("""
            SELECT edge_id, subject_id, object_id, relation_type 
            FROM edges
        """)
        
        # Generate GraphML
        graphml = ['<?xml version="1.0" encoding="UTF-8"?>']
        graphml.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        graphml.append('  <graph id="G" edgedefault="directed">')
        
        # Nodes
        for entity in entities:
            entity_id, label, entity_type = entity[0], entity[1], entity[2]
            graphml.append(f'    <node id="{entity_id}">')
            graphml.append(f'      <data key="label">{label}</data>')
            graphml.append(f'      <data key="type">{entity_type}</data>')
            graphml.append('    </node>')
        
        # Edges
        for edge in edges:
            edge_id, subject_id, object_id, relation_type = edge[0], edge[1], edge[2], edge[3]
            graphml.append(f'    <edge id="{edge_id}" source="{subject_id}" target="{object_id}">')
            graphml.append(f'      <data key="relation">{relation_type}</data>')
            graphml.append('    </edge>')
        
        graphml.append('  </graph>')
        graphml.append('</graphml>')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(graphml))
    
    def export_json(self, output_path: str):
        """Export graph to JSON format."""
        # Get all entities
        entities = self.fetchall("SELECT * FROM entities")
        
        # Get all edges
        edges = self.fetchall("SELECT * FROM edges")
        
        # Convert to dict
        graph = {
            'entities': [dict(e) for e in entities],
            'edges': [dict(e) for e in edges]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

