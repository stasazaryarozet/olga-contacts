#!/usr/bin/env python3
"""
Snowballing: Автоматическое расширение графа через веб-поиск
Использует DuckDuckGo (бесплатно, без API ключей)
"""

import sys
import os
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from graph_db import GraphDB
from ie_pipeline import IEPipeline
from entity_resolution import resolve_entities
from utils import log, fetch_url, extract_text


def install_duckduckgo():
    """Install duckduckgo-search if not available."""
    try:
        import duckduckgo_search
    except ImportError:
        log("📦 Installing duckduckgo-search...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search"])
        import duckduckgo_search


def search_web(query, max_results=5):
    """Search web using DuckDuckGo."""
    from duckduckgo_search import DDGS
    
    log(f"🔍 Searching: {query}")
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        urls = []
        for r in results:
            url = r.get('href') or r.get('link')
            if url:
                urls.append({
                    'url': url,
                    'title': r.get('title', ''),
                    'snippet': r.get('body', '')
                })
        
        log(f"   Found {len(urls)} results")
        return urls
    
    except Exception as e:
        log(f"   ⚠️  Search error: {e}")
        return []


def generate_search_queries(db, anchor_name="Ольга Розет", max_entities=10):
    """Generate search queries from graph entities."""
    log(f"\n📋 Generating search queries for: {anchor_name}")
    
    # Get relations for anchor person
    relations = db.get_relations_for_person(anchor_name)
    
    if not relations:
        log(f"   No relations found for {anchor_name}")
        return []
    
    queries = []
    seen_targets = set()
    
    for rel in relations[:max_entities]:
        target_name = rel['target_name']
        
        if target_name in seen_targets:
            continue
        
        seen_targets.add(target_name)
        
        # Generate query
        if rel['target_type'] == 'Organization':
            # "Ольга Розет" + "ВБШД"
            query = f'"{anchor_name}" "{target_name}"'
        elif rel['target_type'] == 'Person':
            # "Ольга Розет" + "Наталья Логинова"
            query = f'"{anchor_name}" "{target_name}"'
        elif rel['target_type'] == 'Event':
            # "Ольга Розет" + "Paris 2026"
            query = f'"{anchor_name}" "{target_name}"'
        else:
            query = f'"{anchor_name}" "{target_name}"'
        
        queries.append({
            'query': query,
            'entity': target_name,
            'entity_type': rel['target_type']
        })
    
    log(f"   Generated {len(queries)} queries")
    return queries


def process_search_results(search_results, ie_pipeline, db):
    """Process URLs from search results through IE pipeline."""
    processed = 0
    
    for i, result in enumerate(search_results, 1):
        url = result['url']
        
        try:
            log(f"\n   [{i}/{len(search_results)}] Fetching: {url}")
            
            # Fetch content
            html = fetch_url(url)
            if not html:
                log(f"      ⚠️  Failed to fetch")
                continue
            
            # Extract text
            text = extract_text(html)
            if len(text) < 200:
                log(f"      ⚠️  Too short ({len(text)} chars)")
                continue
            
            log(f"      Extracted {len(text)} chars")
            
            # Extract with Groq
            result_ie = ie_pipeline.extract(
                text=text,
                source_url=url,
                source_type='web'
            )
            
            if not result_ie:
                log(f"      ⚠️  No extraction result")
                continue
            
            # Entity Resolution
            resolved = resolve_entities(result_ie['entities'])
            
            # Store in graph
            db.store_extraction(
                source_url=url,
                entities=resolved,
                relations=result_ie['relations']
            )
            
            log(f"      ✅ {len(resolved)} entities, {len(result_ie['relations'])} relations")
            
            processed += 1
            
            # Rate limiting
            time.sleep(2)
        
        except Exception as e:
            log(f"      ❌ Error: {e}")
    
    return processed


def main():
    """Main snowballing function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Snowball graph expansion via web search')
    parser.add_argument('--anchor', default='Ольга Розет', help='Anchor person name')
    parser.add_argument('--max-entities', type=int, default=10, 
                       help='Max entities to generate queries from')
    parser.add_argument('--results-per-query', type=int, default=3,
                       help='Max search results per query')
    parser.add_argument('--max-queries', type=int, default=5,
                       help='Max queries to execute')
    
    args = parser.parse_args()
    
    # Check Groq API key
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        log("❌ Error: GROQ_API_KEY not set")
        return 1
    
    # Install DuckDuckGo if needed
    install_duckduckgo()
    
    log("=" * 60)
    log("SNOWBALLING: Graph Expansion via Web Search")
    log("=" * 60)
    
    # Initialize
    db = GraphDB()
    ie_pipeline = IEPipeline(api_key=groq_api_key)
    
    # Get initial stats
    log("\n📊 Initial Graph Stats:")
    stats_before = db.get_stats()
    for key, val in stats_before.items():
        log(f"   {key}: {val}")
    
    # Generate search queries from graph
    queries = generate_search_queries(
        db, 
        anchor_name=args.anchor,
        max_entities=args.max_entities
    )
    
    if not queries:
        log("\n⚠️  No queries generated. Graph is empty or anchor not found.")
        db.close()
        return 1
    
    # Limit queries
    queries = queries[:args.max_queries]
    
    log(f"\n🔎 Executing {len(queries)} search queries...")
    
    # Execute searches and process results
    total_processed = 0
    
    for i, q_info in enumerate(queries, 1):
        log(f"\n[{i}/{len(queries)}] Query: {q_info['query']}")
        log(f"   Entity: {q_info['entity']} ({q_info['entity_type']})")
        
        # Search
        results = search_web(q_info['query'], max_results=args.results_per_query)
        
        if not results:
            log(f"   No results found")
            continue
        
        # Process results
        processed = process_search_results(results, ie_pipeline, db)
        total_processed += processed
        
        # Small delay between queries
        time.sleep(3)
    
    # Final stats
    log("\n" + "=" * 60)
    log("FINAL STATS")
    log("=" * 60)
    
    stats_after = db.get_stats()
    
    log("\n📊 Graph Growth:")
    for key in stats_before.keys():
        before = stats_before[key]
        after = stats_after[key]
        diff = after - before
        log(f"   {key}: {before} → {after} (+{diff})")
    
    log(f"\n✅ Snowballing completed")
    log(f"   Queries executed: {len(queries)}")
    log(f"   URLs processed: {total_processed}")
    
    db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

