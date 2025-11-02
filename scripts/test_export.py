"""
Test export functionality: GraphML and JSON
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from enhanced_graph_db import EnhancedGraphDB


def test_export():
    """Test GraphML and JSON export."""
    
    print("📤 Тестирование экспорта графа...")
    print()
    
    # Open database
    db = EnhancedGraphDB()
    
    # Export to GraphML
    print("  1️⃣  Экспорт в GraphML (для Gephi, Neo4j)...")
    db.export_to_graphml("data/olga_contacts.graphml")
    print("     ✅ data/olga_contacts.graphml")
    print()
    
    # Export to JSON
    print("  2️⃣  Экспорт в JSON (для D3.js, web UI)...")
    db.export_to_json("data/olga_contacts.json")
    print("     ✅ data/olga_contacts.json")
    print()
    
    # Get stats
    stats = db.get_stats()
    
    print("📊 Статистика экспортированного графа:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print()
    print("🎯 Использование:")
    print("  • GraphML: Откройте в Gephi для визуализации")
    print("  • JSON: Используйте в D3.js для web UI")
    
    # Close
    db.close()


if __name__ == "__main__":
    test_export()

