"""SQLite Graph Database with Fact Reification."""

import sqlite3
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


class GraphDB:
    """SQLite-based Graph Database."""
    
    def __init__(self, db_path: str = "data/contacts.db"):
        """Initialize SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
    
    def _create_schema(self):
        """Create database schema."""
        cursor = self.conn.cursor()
        
        # Sources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                url TEXT PRIMARY KEY,
                authority REAL DEFAULT 1.0,
                first_seen TIMESTAMP,
                last_processed TIMESTAMP
            )
        """)
        
        # Nodes table (entities)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                canonical_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,  -- Person, Organization
                metadata TEXT,  -- JSON
                first_seen TIMESTAMP
            )
        """)
        
        # Facts table (reified relations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                relation_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                object_id TEXT NOT NULL,
                start_date TEXT,  -- ISO date
                end_date TEXT,    -- ISO date or NULL
                confidence REAL NOT NULL,
                context TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES nodes(canonical_id),
                FOREIGN KEY (object_id) REFERENCES nodes(canonical_id)
            )
        """)
        
        # Claims table (source -> fact)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                source_url TEXT NOT NULL,
                fact_id TEXT NOT NULL,
                confidence_llm REAL NOT NULL,
                PRIMARY KEY (source_url, fact_id),
                FOREIGN KEY (source_url) REFERENCES sources(url),
                FOREIGN KEY (fact_id) REFERENCES facts(fact_id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_object ON facts(object_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(relation_type)")
        
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def store_fact(self, fact: Dict[str, Any]):
        """Store a single fact with reification."""
        cursor = self.conn.cursor()
        
        # 1. Insert/update Source
        cursor.execute("""
            INSERT INTO sources (url, authority, first_seen, last_processed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET last_processed = ?
        """, (
            fact["source_url"],
            fact.get("authority", 1.0),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # 2. Insert Nodes (subject and object) if not exist
        for node_key in ["subject", "object"]:
            cursor.execute("""
                INSERT OR IGNORE INTO nodes (canonical_id, name, type, first_seen)
                VALUES (?, ?, ?, ?)
            """, (
                fact[f"{node_key}_canonical_id"],
                fact[f"{node_key}_name"],
                fact[f"{node_key}_type"],
                datetime.now().isoformat()
            ))
        
        # 3. Insert Fact
        cursor.execute("""
            INSERT OR REPLACE INTO facts 
            (fact_id, relation_type, subject_id, object_id, start_date, end_date, 
             confidence, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fact["fact_id"],
            fact["relation_type"],
            fact["subject_canonical_id"],
            fact["object_canonical_id"],
            fact.get("start_date"),
            fact.get("end_date"),
            fact["confidence"],
            fact.get("context", ""),
            datetime.now().isoformat()
        ))
        
        # 4. Insert Claim
        cursor.execute("""
            INSERT OR REPLACE INTO claims (source_url, fact_id, confidence_llm)
            VALUES (?, ?, ?)
        """, (
            fact["source_url"],
            fact["fact_id"],
            fact["confidence"]
        ))
        
        self.conn.commit()
    
    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL query."""
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Node counts by type
        cursor.execute("SELECT type, COUNT(*) as count FROM nodes GROUP BY type")
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        
        # Total facts
        cursor.execute("SELECT COUNT(*) FROM facts")
        stats["Facts"] = cursor.fetchone()[0]
        
        # Total sources
        cursor.execute("SELECT COUNT(*) FROM sources")
        stats["Sources"] = cursor.fetchone()[0]
        
        return stats
    
    def get_relations_for_person(self, person_name: str) -> List[Dict[str, Any]]:
        """Get all relations for a person."""
        sql = """
            SELECT 
                f.relation_type,
                n_obj.name as target_name,
                n_obj.type as target_type,
                f.start_date,
                f.end_date,
                f.confidence,
                f.context
            FROM facts f
            JOIN nodes n_subj ON f.subject_id = n_subj.canonical_id
            JOIN nodes n_obj ON f.object_id = n_obj.canonical_id
            WHERE n_subj.name = ?
            ORDER BY f.confidence DESC, f.start_date DESC
        """
        return self.query(sql, (person_name,))
    
    def export_graph_json(self, output_path: str = "data/graph.json"):
        """Export graph to JSON for visualization."""
        # Get all nodes
        nodes = self.query("SELECT canonical_id, name, type FROM nodes")
        
        # Get all facts with source info
        facts = self.query("""
            SELECT 
                f.*,
                n_subj.name as subject_name,
                n_obj.name as object_name,
                s.url as source_url
            FROM facts f
            JOIN nodes n_subj ON f.subject_id = n_subj.canonical_id
            JOIN nodes n_obj ON f.object_id = n_obj.canonical_id
            JOIN claims c ON f.fact_id = c.fact_id
            JOIN sources s ON c.source_url = s.url
        """)
        
        graph = {
            "nodes": nodes,
            "edges": facts,
            "metadata": {
                "created": datetime.now().isoformat(),
                "stats": self.get_stats()
            }
        }
        
        Path(output_path).parent.mkdir(exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        
        return output_path
