#!/usr/bin/env python3
"""
Autonomous Contact Graph Builder
Budget = 0, Quality ≥ 0.85

Cron job: 0 3 * * * cd /path/to/contacts && ./venv/bin/python src/main.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from ie_pipeline import IEPipeline
from entity_resolution import EntityResolver
from graph_db import GraphDB
from utils import fetch_url, extract_text, generate_fact_id, log


def main():
    """Main execution function."""
    # Load environment
    load_dotenv()
    
    # Config
    seed_file = Path(__file__).parent.parent / "config" / "seed.txt"
    
    if not seed_file.exists():
        log("❌ seed.txt not found! Create config/seed.txt with URLs")
        return 1
    
    log("=" * 60)
    log(f"🚀 Autonomous Contact Graph Builder v1.0")
    log(f"   Run started at {datetime.now()}")
    log("=" * 60)
    
    # Initialize components
    try:
        ie_pipeline = IEPipeline()
        er = EntityResolver()
        db = GraphDB()
        log("✓ Components initialized")
    except Exception as e:
        log(f"❌ Initialization failed: {e}")
        return 1
    
    # Read seed URLs
    urls = [line.strip() for line in seed_file.read_text().splitlines() 
            if line.strip() and not line.startswith("#")]
    log(f"📋 Found {len(urls)} seed URLs")
    
    # Process each URL
    total_facts = 0
    failed_urls = []
    
    for idx, url in enumerate(urls, 1):
        log(f"\n[{idx}/{len(urls)}] Processing: {url}")
        
        try:
            # 1. Fetch HTML
            html = fetch_url(url)
            if not html:
                failed_urls.append((url, "Failed to fetch"))
                continue
            
            # 2. Extract text
            text = extract_text(html)
            if len(text) < 100:
                log(f"⚠️  Text too short ({len(text)} chars), skipping")
                failed_urls.append((url, "Text too short"))
                continue
            
            log(f"   Extracted {len(text)} characters")
            
            # 3. IE Pipeline (Groq API)
            source_type = ie_pipeline.detect_source_type(url)
            log(f"   Source type: {source_type}")
            
            result = ie_pipeline.extract(text, source_type, url)
            
            if "error" in result:
                log(f"⚠️  IE Pipeline error: {result['error']}")
                failed_urls.append((url, result['error']))
                continue
            
            num_entities = len(result.get("entities", []))
            num_relations = len(result.get("relations", []))
            log(f"   Extracted: {num_entities} entities, {num_relations} relations")
            
            if num_relations == 0:
                log("   ℹ️  No relations found")
                continue
            
            # 4. Entity Resolution
            entities = er.resolve(result["entities"])
            log(f"   After ER: {len(entities)} canonical entities")
            
            # 5. Store to Neo4j
            for relation in result["relations"]:
                try:
                    # Build fact dict
                    fact = {
                        "source_url": url,
                        "authority": 1.0,  # Seed = high authority
                        "fact_id": generate_fact_id(relation),
                        "relation_type": relation["relation"],
                        "subject_name": relation["subject"]["name"],
                        "subject_type": relation["subject"].get("type", "Person"),
                        "subject_canonical_id": f"temp:{relation['subject']['name']}",  # Will be improved with ER
                        "object_name": relation["object"]["name"],
                        "object_type": relation["object"].get("type", "Organization"),
                        "object_canonical_id": f"temp:{relation['object']['name']}",
                        "start_date": relation.get("temporal", {}).get("start_iso"),
                        "end_date": relation.get("temporal", {}).get("end_iso"),
                        "confidence": relation.get("confidence", 0.8),
                        "context": relation.get("context", "")
                    }
                    
                    db.store_fact(fact)
                    total_facts += 1
                    
                except Exception as e:
                    log(f"   ⚠️  Failed to store relation: {e}")
            
            log(f"   ✓ Stored {num_relations} facts")
            
        except Exception as e:
            log(f"❌ Error processing {url}: {e}")
            failed_urls.append((url, str(e)))
    
    # Summary
    log("\n" + "=" * 60)
    log("📊 Run Summary")
    log("=" * 60)
    log(f"   URLs processed: {len(urls) - len(failed_urls)}/{len(urls)}")
    log(f"   Total facts stored: {total_facts}")
    
    if failed_urls:
        log(f"\n⚠️  Failed URLs ({len(failed_urls)}):")
        for url, reason in failed_urls:
            log(f"   - {url}: {reason}")
    
    # Database stats
    try:
        stats = db.get_stats()
        log(f"\n📈 Database Stats:")
        for label, count in stats.items():
            if not label.startswith("_"):
                log(f"   {label}: {count} nodes")
        log(f"   Relationships: {sum(stats.get('_relationships', {}).values())}")
    except Exception as e:
        log(f"⚠️  Could not get stats: {e}")
    
    # Cleanup
    db.close()
    
    log(f"\n✓ Run completed at {datetime.now()}")
    log("=" * 60)
    
    return 0 if not failed_urls else 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

