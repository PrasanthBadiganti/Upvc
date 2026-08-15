#!/bin/bash

echo "🔄 Resetting database and loading test data..."
echo ""

# Kill any running backend processes
echo "⏹️  Stopping backend server..."
pkill -f "python.*main.py" || true
sleep 2

# Delete the database file
echo "🗑️  Deleting existing database..."
rm -f upvc_pro.db

# Start the backend server (it will recreate the database)
echo "🚀 Starting backend server..."
python -m uvicorn app.main:app --reload &
BACKEND_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server to initialize..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/catalog > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    echo "  Attempt $i/30..."
    sleep 1
done

# Run the data loader
echo ""
echo "📦 Loading test data..."
python load_test_data.py

echo ""
echo "✨ Done! Database is ready with test data."
echo "Backend PID: $BACKEND_PID"
