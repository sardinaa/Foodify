#!/bin/bash

# Foodify Quick Start Script

echo "🍳 Starting Foodify..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the Foodify root directory"
    exit 1
fi

# Start backend
echo "📦 Starting backend..."

# Check if virtual environment exists in backend
if [ ! -d "backend/venv" ]; then
    echo "Creating virtual environment in backend..."
    cd backend
    python3 -m venv venv
    cd ..
fi

source backend/venv/bin/activate
pip install -q -r backend/requirements.txt

cd backend
echo "🚀 Backend starting on http://localhost:8000"
PYTHONPATH=. python3 -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

cd ..

# Start frontend
echo "📦 Starting frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo "🚀 Frontend starting on http://localhost:3000"
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "✅ Foodify is running!"
echo ""
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
