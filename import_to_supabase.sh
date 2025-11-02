#!/bin/bash
# Import data to Supabase PostgreSQL via Session Pooler
# Run: bash import_to_supabase.sh

set -e  # Exit on error

echo "🔗 Supabase Data Import Script"
echo "================================"
echo ""

# Step 1: Get connection string from user
echo "📋 Step 1: Get your Session Pooler connection string"
echo ""
echo "In Supabase Dashboard:"
echo "  1. Settings → Database → Connection pooling"
echo "  2. Select 'Session mode'"
echo "  3. Copy the connection string"
echo ""
echo "Expected format:"
echo "  postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres"
echo ""
read -p "Paste your connection string here: " DATABASE_URL
echo ""

# Step 2: Validate format
if [[ ! "$DATABASE_URL" =~ pooler\.supabase\.com:5432 ]]; then
    echo "❌ Error: Connection string must contain 'pooler.supabase.com:5432'"
    echo "   Make sure you're using Session Pooler (not direct connection)"
    exit 1
fi

if [[ ! "$DATABASE_URL" =~ ^postgresql:// ]]; then
    echo "❌ Error: Connection string must start with 'postgresql://'"
    exit 1
fi

echo "✅ Connection string format looks correct"
echo ""

# Step 3: Test connection
echo "🧪 Step 2: Testing connection..."
if psql "$DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Connection successful!"
else
    echo "❌ Connection failed. Please check:"
    echo "   - Password is correct"
    echo "   - Pooler is enabled in Supabase"
    echo "   - Your IP is not blocked"
    exit 1
fi
echo ""

# Step 4: Import data
echo "📥 Step 3: Importing data from migration_data.sql..."
echo "   (This may take 1-2 minutes for 6898 INSERT statements)"
echo ""

# Set timeout to 0 (unlimited) for large import
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<EOF
SET statement_timeout = 0;
\i migration_data.sql
EOF

if [ $? -eq 0 ]; then
    echo "✅ Data imported successfully!"
else
    echo "❌ Import failed. Check errors above."
    exit 1
fi
echo ""

# Step 5: Verify data
echo "📊 Step 4: Verifying imported data..."
psql "$DATABASE_URL" -c "
SELECT 
    (SELECT COUNT(*) FROM entities) as entities,
    (SELECT COUNT(*) FROM edges) as edges,
    (SELECT COUNT(*) FROM sources) as sources,
    (SELECT COUNT(*) FROM identifiers) as identifiers,
    (SELECT COUNT(*) FROM raw_data) as raw_data;
"
echo ""

echo "✅ Expected counts:"
echo "   - entities: 464"
echo "   - edges: 5050"
echo "   - sources: 460"
echo "   - identifiers: 464"
echo ""

echo "🎉 Import complete!"
echo ""
echo "Next step: Deploy to Streamlit Cloud"
echo "   See: FINAL_DEPLOYMENT_STEPS.md (Step 4)"

