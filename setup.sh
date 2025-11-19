#!/bin/bash

# Foodify Setup & Validation Script

set -e  # Exit on error

echo "🍳 Foodify Setup & Validation"
echo "=============================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 not found"
    exit 1
fi

# Node
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Node.js: $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Node.js not found"
    exit 1
fi

# npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} npm: $NPM_VERSION"
else
    echo -e "${RED}✗${NC} npm not found"
    exit 1
fi

echo ""
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${GREEN}✓${NC} Backend dependencies installed"

# Check backend imports
echo "Validating backend imports..."
if python3 -c "from app.main import app; print('Backend imports OK')" 2>&1 | grep -q "Backend imports OK"; then
    echo -e "${GREEN}✓${NC} Backend imports successful"
else
    echo -e "${RED}✗${NC} Backend import errors"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠${NC} .env file not found, copying from .env.example"
    cp .env.example .env
fi

cd ..

echo ""
echo "📦 Setting up Frontend..."
cd frontend

# Install npm dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
else
    echo -e "${GREEN}✓${NC} npm dependencies already installed"
fi

# Check .env.local
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}⚠${NC} .env.local not found, creating..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
fi

# Build frontend to check for errors
echo "Validating frontend build..."
if npm run build > /tmp/nextjs-build.log 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend builds successfully"
else
    echo -e "${RED}✗${NC} Frontend build errors:"
    cat /tmp/nextjs-build.log | tail -20
    exit 1
fi

cd ..

echo ""
echo "📊 Checking data files..."
if [ -f "data/nutrition_data.csv" ]; then
    LINES=$(wc -l < data/nutrition_data.csv)
    echo -e "${GREEN}✓${NC} nutrition_data.csv found ($LINES lines)"
else
    echo -e "${RED}✗${NC} nutrition_data.csv not found in data/"
    exit 1
fi

echo ""
echo "🔍 Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓${NC} Ollama installed"
    
    # Check if models are available
    if ollama list 2>&1 | grep -q "llama3.2"; then
        echo -e "${GREEN}✓${NC} llama3.2 model found"
    else
        echo -e "${YELLOW}⚠${NC} llama3.2 model not found"
        echo "  Run: ollama pull llama3.2"
    fi
    
    if ollama list 2>&1 | grep -q "llama3.2-vision"; then
        echo -e "${GREEN}✓${NC} llama3.2-vision model found"
    else
        echo -e "${YELLOW}⚠${NC} llama3.2-vision model not found"
        echo "  Run: ollama pull llama3.2-vision"
    fi
else
    echo -e "${YELLOW}⚠${NC} Ollama not found (optional for demo)"
    echo "  Install from: https://ollama.ai"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  Backend:  cd backend && source venv/bin/activate && python3 -m app.main"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use the convenience script:"
echo "  ./start.sh"
