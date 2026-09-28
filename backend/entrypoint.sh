#!/bin/sh
set -e

echo "=== [SkillSprint AI] Initializing Container Database ==="
python setup_database.py

echo "=== [SkillSprint AI] Starting FastAPI Application ==="
cd /app/backend
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
