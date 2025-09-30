#!/bin/bash

# Print environment info for debugging
echo "🚀 Starting Novarsis Chatbot on Render"
echo "📊 Python Version: $(python --version)"
echo "🔧 Environment Variables Check:"

# Check if MongoDB URL is set
if [ -z "$MONGODB_URL" ]; then
    echo "⚠️  WARNING: MONGODB_URL not found in environment variables"
    echo "   MongoDB features will be disabled"
else
    echo "✅ MONGODB_URL is configured"
    # Hide actual URL for security
    echo "   MongoDB Host: $(echo $MONGODB_URL | sed 's/mongodb+srv:\/\/[^@]*@/***@/' | cut -d'/' -f3)"
fi

# Check other required env vars
if [ -z "$OLLAMA_API_KEY" ]; then
    echo "⚠️  WARNING: OLLAMA_API_KEY not found"
fi

echo "🌐 Starting server on port: ${PORT:-8000}"
echo "======================================"

# Start the application with proper host and port binding
uvicorn novars2:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info
