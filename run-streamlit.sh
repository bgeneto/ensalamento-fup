#!/bin/bash
# Run the legacy Streamlit application for comparison/testing
# Usage: ./run-streamlit.sh

set -e

echo "🚀 Starting Streamlit Legacy Application..."
echo "📍 URL: http://localhost:8501"
echo "🔧 Using shared data directory: ./data/"
echo "📊 Using shared logs directory: ./logs/"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

docker-compose --profile legacy up streamlit-legacy
