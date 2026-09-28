"""SkillSprint AI - Database Setup and Ingestion Script.

Designed for team members and competition evaluators to initialize or reset
the entire application database in a single command.

Usage:
    python setup_database.py            # Initialize missing tables, seed data & ingest 28 docs
    python setup_database.py --reset    # Wipe clean and recreate everything from scratch
"""
from pathlib import Path
import sys

# Forward to root setup_database.py or run directly
ROOT_SETUP = Path(__file__).resolve().parents[1] / "setup_database.py"
if ROOT_SETUP.is_file():
    exec(ROOT_SETUP.read_text(encoding="utf-8"))
else:
    raise FileNotFoundError("Root setup_database.py not found.")
