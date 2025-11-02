"""Deterministic Entity Resolution."""

import uuid
from typing import List, Dict, Any


class EntityResolver:
    """Deterministic Entity Resolution (exact match only)."""
    
    def __init__(self):
        self.merged_entities = {}
    
    def resolve(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge entities using deterministic rules.
        
        Rules:
        1. Exact email match
        2. Exact LinkedIn URL match
        3. Exact name + organization match
        
        Args:
            entities: List of extracted entities
            
        Returns:
            List of merged entities with canonical IDs
        """
        merged = {}
        
        for entity in entities:
            key = self._generate_key(entity)
            
            if key in merged:
                # Merge: append source
                merged[key]["sources"].append(entity.get("source", "unknown"))
                # Keep highest confidence
                if entity.get("confidence", 0) > merged[key].get("confidence", 0):
                    merged[key]["confidence"] = entity["confidence"]
            else:
                # New entity
                entity["canonical_id"] = key
                entity["sources"] = [entity.get("source", "unknown")]
                merged[key] = entity
        
        return list(merged.values())
    
    def _generate_key(self, entity: Dict[str, Any]) -> str:
        """Generate unique key for entity."""
        # Rule 1: Email (highest priority)
        if entity.get("email"):
            return f"email:{entity['email'].lower().strip()}"
        
        # Rule 2: LinkedIn URL
        if entity.get("linkedin"):
            linkedin = entity["linkedin"].lower().strip()
            # Normalize: remove trailing slashes, etc.
            linkedin = linkedin.rstrip("/")
            return f"linkedin:{linkedin}"
        
        # Rule 3: Name + Organization
        if entity.get("name") and entity.get("organization"):
            name = self._normalize_name(entity["name"])
            org = entity["organization"].lower().strip()
            return f"name_org:{name}:{org}"
        
        # Rule 4: Just name (will create duplicates, but safe)
        if entity.get("name"):
            name = self._normalize_name(entity["name"])
            return f"name:{name}:{uuid.uuid4()}"  # Unique per occurrence
        
        # Fallback: unique ID
        return f"unique:{uuid.uuid4()}"
    
    def _normalize_name(self, name: str) -> str:
        """Normalize person name for matching."""
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Future: could add transliteration, remove initials, etc.
        # For MVP: simple normalization
        
        return name


# Convenience function for backward compatibility
def resolve_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resolve entities using EntityResolver."""
    resolver = EntityResolver()
    return resolver.resolve(entities)

