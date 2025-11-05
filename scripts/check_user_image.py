import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "elegance.db"
if not db.exists():
    print("DB introuvable:", db); raise SystemExit(1)

conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute("SELECT id, email, profile_image FROM user WHERE id=?", (3,))  # change 3 -> ton user_id
print(cur.fetchone())
conn.close()