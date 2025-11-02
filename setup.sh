#!/bin/bash
# Setup script for Contact Graph Builder

set -e

echo "🚀 Contact Graph Builder Setup"
echo "================================"

# 1. Check Python version
echo "→ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found! Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION"

# 2. Create virtual environment
echo "→ Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# 3. Activate and install dependencies
echo "→ Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# 4. Check Neo4j
echo "→ Checking Neo4j..."
if ! command -v neo4j &> /dev/null; then
    echo "⚠️  Neo4j not found!"
    echo "   Please install Neo4j Desktop from: https://neo4j.com/download/"
    echo "   Then create a local database with password 'contacts'"
else
    echo "✓ Neo4j found"
fi

# 5. Setup .env
echo "→ Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file"
    echo "   ⚠️  IMPORTANT: Edit .env and add your GROQ_API_KEY"
    echo "   Get key from: https://console.groq.com"
else
    echo "✓ .env exists"
fi

# 6. Create log directory
mkdir -p logs
echo "✓ Log directory created"

# 7. Test imports
echo "→ Testing imports..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from ie_pipeline import IEPipeline
from entity_resolution import EntityResolver
from graph_db import GraphDB
print('✓ All modules import successfully')
"

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Get Groq API key from https://console.groq.com (FREE)"
echo "2. Edit .env and add your GROQ_API_KEY"
echo "3. Install Neo4j Desktop and create database 'contacts'"
echo "4. Edit config/seed.txt with 10-20 URLs about Ольга Розет"
echo "5. Run: python3 src/main.py"
echo ""

