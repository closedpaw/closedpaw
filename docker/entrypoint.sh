#!/bin/bash
set -e

echo "🔒 ClosedPaw - Zero-Trust AI Assistant"
echo "========================================"

# Start backend
echo "Starting backend..."
cd /app/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo "Starting frontend..."
cd /app/frontend
npm run start -- -H 0.0.0.0 -p 3000 &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo ""
echo "✅ ClosedPaw is running!"
echo ""
echo "🌐 Web UI: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"

# Wait
wait
