#!/bin/bash
# Run the new Reflex application
# Usage: ./run-reflex.sh

set -e

echo "🚀 Starting Reflex Application (Development)..."
echo "📍 Application accessed at: http://localhost:8000"
echo "(Reflex serves both frontend and backend on port 8000 in development mode)"
echo ""
echo "🔧 Using shared SQLite database: ./data/"
echo "📊 Logs stored in: ./logs/"
echo ""
echo "Test login credentials:"
echo "  Username: admin      Password: admin123"
echo "  Username: professor  Password: prof123"
echo ""
echo "Navigate to Allocation page to test real-time allocation!"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

# Set up environment and run Reflex directly
cd reflex || exit 1

echo "📁 Running from: $(pwd)"
echo "🐍 Python path: $(which python)"
echo "🧠 Using virtual environment: $VIRTUAL_ENV"
echo ""

# Install reflex and run the app
# pip install reflex==0.8.19 || echo "Could not install reflex, trying existing packages"

# Run the Reflex app directly
PYTHONPATH=/home/bgeneto/github/ensalamento-fup reflex run --backend-port 8000 --frontend-port 3000
