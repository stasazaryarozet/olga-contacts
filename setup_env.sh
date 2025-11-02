#!/bin/bash
# Setup script for Contact Graph Builder
# Run: source setup_env.sh

# Groq API Key
export GROQ_API_KEY="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"

# Gmail credentials (to be filled)
# Uncomment and fill after creating Gmail App Password:
# export GMAIL_EMAIL="olga.email@gmail.com"
# export GMAIL_PASSWORD="your_16_char_app_password"

echo "✅ Environment variables loaded"
echo "   GROQ_API_KEY: ${GROQ_API_KEY:0:10}...${GROQ_API_KEY: -4}"

if [ -z "$GMAIL_EMAIL" ]; then
    echo "⚠️  GMAIL_EMAIL not set (needed for Email Pipeline)"
fi

if [ -z "$GMAIL_PASSWORD" ]; then
    echo "⚠️  GMAIL_PASSWORD not set (needed for Email Pipeline)"
fi

