from pathlib import Path
import os
import shutil
import sys

db_path = Path(os.getenv("DATABASE_PATH", "questions.db"))
seed_db = Path("questions.db")

db_path.parent.mkdir(parents=True, exist_ok=True)

if not db_path.exists() and seed_db.exists() and db_path.resolve() != seed_db.resolve():
    print(f"Copying seed database from {seed_db} to {db_path}")
    shutil.copy(seed_db, db_path)

print(f"Starting bot with database: {db_path}")
os.execv(sys.executable, [sys.executable, "bot.py"])
