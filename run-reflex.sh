#!/bin/bash
# Run the new Reflex application
# Usage: ./run-reflex.sh

set -e

echo "🚀 Starting Reflex Application (Development)..."
echo "📍 URL: http://localhost:8000"
echo "🔧 Using shared data directory: ./data/"
echo "📊 Using shared logs directory: ./logs/"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

docker-compose --profile reflex up reflex
