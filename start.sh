#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Starting Compete"
echo ""

# Backend
cd "$ROOT/backend"
if [ ! -d venv ]; then
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt -q
fi

export DB_PATH="$ROOT/compete.db"
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend running on http://localhost:8000 (PID $BACKEND_PID)"

# Frontend
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install -q
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend running on http://localhost:5173 (PID $FRONTEND_PID)"

echo ""
echo "Open: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
