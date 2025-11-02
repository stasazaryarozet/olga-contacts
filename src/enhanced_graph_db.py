"""
Enhanced Graph Database with Entity Resolution and Canonical IDs
Implements Gemini's recommendations for maximum plasticity and reusability.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class EnhancedGraphDB:
    """
    Enhanced graph database with:
    1. Canonical IDs (Entity Resolution)
    2. Graph Zone / Context Zone separation
    3. Unified fact gateway (add_fact)
    4. Export capabilities (GraphML, JSON)
    """
    
    def __init__(self, db_path="data/contacts_v2.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_enhanced_schema()
    
    def _create_enhanced_schema(self):
        """Create enhanced database schema."""
        
        # ============================================================
        # GRAPH ZONE: Fast, clean, query-ready
        # ============================================================
        
        # Entities (canonical) - Enhanced schema for business contacts
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
        
        # Identifiers (many-to-one with entities)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS identifiers (
                identifier TEXT PRIMARY KEY,
                entity_id INTEGER NOT NULL,
                identifier_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
            )
        """)
        
        # Edges (relations between entities)
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
                FOREIGN KEY (object_id) REFERENCES entities(entity_id),
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            )
        """)
        
        # Indexes for fast queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_subject ON edges(subject_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_object ON edges(object_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id)
        """)
        
        # Business contacts indexes
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_relationship_strength 
            ON entities(relationship_strength DESC)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_last_interaction 
            ON entities(last_interaction DESC)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)
        """)
        
        # ============================================================
        # CONTEXT ZONE: Slow, "dirty", for provenance only
        # ============================================================
        
        # Sources (files, APIs, etc)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                source_type TEXT,
                hash TEXT UNIQUE,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Raw data (original events, emails, etc)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                data_type TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            )
        """)
        
        self.conn.commit()
    
    def get_or_create_entity(
        self, 
        identifier: str, 
        label: Optional[str] = None,
        entity_type: str = "Person",
        identifier_type: str = "email"
    ) -> int:
        """
        Get existing entity or create new one (with canonical ID).
        
        This is the core of Entity Resolution.
        
        Args:
            identifier: Email, name, or other identifier
            label: Human-readable name (if creating new)
            entity_type: Person, Organization, Event
            identifier_type: email, name, etc
            
        Returns:
            entity_id (canonical)
        """
        # Check if identifier exists
        cursor = self.conn.execute("""
            SELECT entity_id FROM identifiers WHERE identifier = ?
        """, (identifier,))
        
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new entity
        cursor = self.conn.execute("""
            INSERT INTO entities (label, type)
            VALUES (?, ?)
        """, (label or identifier, entity_type))
        
        entity_id = cursor.lastrowid
        
        # Create identifier
        self.conn.execute("""
            INSERT INTO identifiers (identifier, entity_id, identifier_type)
            VALUES (?, ?, ?)
        """, (identifier, entity_id, identifier_type))
        
        self.conn.commit()
        
        return entity_id
    
    def add_identifier(self, identifier: str, entity_id: int, identifier_type: str = "email"):
        """Add additional identifier to existing entity."""
        try:
            self.conn.execute("""
                INSERT INTO identifiers (identifier, entity_id, identifier_type)
                VALUES (?, ?, ?)
            """, (identifier, entity_id, identifier_type))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Identifier already exists
            pass
    
    def add_fact(
        self,
        subject: str,
        relation: str,
        object: str,
        source_details: Dict,
        event_date: Optional[str] = None,
        confidence: float = 1.0,
        subject_label: Optional[str] = None,
        object_label: Optional[str] = None,
        subject_type: str = "Person",
        object_type: str = "Person"
    ) -> int:
        """
        Universal gateway for adding any fact to the graph.
        
        This is the ONLY function that should be called by parsers.
        
        Args:
            subject: Subject identifier (email, name)
            relation: Relation type (co_attended, works_at, etc)
            object: Object identifier
            source_details: Dict with filename, type, content
            event_date: Date of the event/relation
            confidence: Confidence score (0-1)
            subject_label: Human-readable label for subject
            object_label: Human-readable label for object
            subject_type: Entity type for subject
            object_type: Entity type for object
            
        Returns:
            edge_id
        """
        # 1. Get or create canonical IDs
        subject_id = self.get_or_create_entity(
            subject, 
            label=subject_label,
            entity_type=subject_type
        )
        
        object_id = self.get_or_create_entity(
            object,
            label=object_label,
            entity_type=object_type
        )
        
        # 2. Save context (source)
        source_id = self._save_context(source_details)
        
        # 3. Save edge
        cursor = self.conn.execute("""
            INSERT INTO edges (
                subject_id, object_id, relation_type, 
                event_date, confidence, source_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (subject_id, object_id, relation, event_date, confidence, source_id))
        
        self.conn.commit()
        
        return cursor.lastrowid
    
    def _save_context(self, source_details: Dict) -> int:
        """Save source context (Context Zone)."""
        filename = source_details.get('filename', 'unknown')
        source_type = source_details.get('type', 'unknown')
        content = source_details.get('content', '')
        
        # Create hash for deduplication
        content_hash = hashlib.md5(
            f"{filename}:{content}".encode()
        ).hexdigest()
        
        # Check if source exists
        cursor = self.conn.execute("""
            SELECT source_id FROM sources WHERE hash = ?
        """, (content_hash,))
        
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new source
        cursor = self.conn.execute("""
            INSERT INTO sources (filename, source_type, hash)
            VALUES (?, ?, ?)
        """, (filename, source_type, content_hash))
        
        source_id = cursor.lastrowid
        
        # Save raw data
        self.conn.execute("""
            INSERT INTO raw_data (source_id, data_type, content)
            VALUES (?, ?, ?)
        """, (source_id, source_type, content))
        
        self.conn.commit()
        
        return source_id
    
    def export_to_graphml(self, output_file: str):
        """Export graph to GraphML format (for Gephi, Neo4j, etc)."""
        import xml.etree.ElementTree as ET
        
        # Create GraphML structure
        graphml = ET.Element('graphml', xmlns="http://graphml.graphdrawing.org/xmlns")
        
        # Define keys (attributes)
        ET.SubElement(graphml, 'key', id="label", **{
            'for': 'node',
            'attr.name': 'label',
            'attr.type': 'string'
        })
        ET.SubElement(graphml, 'key', id="type", **{
            'for': 'node',
            'attr.name': 'type',
            'attr.type': 'string'
        })
        ET.SubElement(graphml, 'key', id="relation", **{
            'for': 'edge',
            'attr.name': 'relation',
            'attr.type': 'string'
        })
        ET.SubElement(graphml, 'key', id="confidence", **{
            'for': 'edge',
            'attr.name': 'confidence',
            'attr.type': 'double'
        })
        
        # Create graph
        graph = ET.SubElement(graphml, 'graph', id="G", edgedefault="directed")
        
        # Add nodes
        cursor = self.conn.execute("SELECT entity_id, label, type FROM entities")
        for entity_id, label, entity_type in cursor.fetchall():
            node = ET.SubElement(graph, 'node', id=str(entity_id))
            ET.SubElement(node, 'data', key='label').text = label
            ET.SubElement(node, 'data', key='type').text = entity_type
        
        # Add edges
        cursor = self.conn.execute("""
            SELECT edge_id, subject_id, object_id, relation_type, confidence
            FROM edges
        """)
        for edge_id, subject_id, object_id, relation, confidence in cursor.fetchall():
            edge = ET.SubElement(graph, 'edge', 
                id=str(edge_id),
                source=str(subject_id),
                target=str(object_id)
            )
            ET.SubElement(edge, 'data', key='relation').text = relation
            ET.SubElement(edge, 'data', key='confidence').text = str(confidence)
        
        # Write to file
        tree = ET.ElementTree(graphml)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
    
    def export_to_json(self, output_file: str):
        """Export graph to JSON format (for D3.js, web visualization)."""
        # Get nodes
        cursor = self.conn.execute("SELECT entity_id, label, type FROM entities")
        nodes = [
            {
                'id': entity_id,
                'label': label,
                'type': entity_type
            }
            for entity_id, label, entity_type in cursor.fetchall()
        ]
        
        # Get edges
        cursor = self.conn.execute("""
            SELECT subject_id, object_id, relation_type, confidence
            FROM edges
        """)
        edges = [
            {
                'source': subject_id,
                'target': object_id,
                'relation': relation,
                'confidence': confidence
            }
            for subject_id, object_id, relation, confidence in cursor.fetchall()
        ]
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'nodes': nodes,
                'links': edges
            }, f, ensure_ascii=False, indent=2)
    
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        stats = {}
        
        # Entities by type
        cursor = self.conn.execute("""
            SELECT type, COUNT(*) FROM entities GROUP BY type
        """)
        for entity_type, count in cursor.fetchall():
            stats[entity_type] = count
        
        # Total edges
        cursor = self.conn.execute("SELECT COUNT(*) FROM edges")
        stats['Edges'] = cursor.fetchone()[0]
        
        # Sources
        cursor = self.conn.execute("SELECT COUNT(*) FROM sources")
        stats['Sources'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection."""
        self.conn.close()

