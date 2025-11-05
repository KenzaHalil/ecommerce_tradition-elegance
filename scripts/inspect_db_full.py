import sqlite3
from pathlib import Path
import sys
import json

PROJECT = Path(__file__).resolve().parents[1]
DB = PROJECT / "elegance.db"

if not DB.exists():
    print("DB introuvable:", DB); sys.exit(1)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("Tables trouvées:", tables)

for t in tables:
    print("\n--- TABLE:", t)
    try:
        cols = cur.execute(f"PRAGMA table_info('{t}')").fetchall()
        print("Colonnes:", [c[1] + ' (' + c[2] + ')' for c in cols])
        print("Création SQL:")
        for r in cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)):
            print(r[0])
        print("Nombre de lignes:", cur.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0])
        print("Échantillon (max 5 lignes):")
        for row in cur.execute(f"SELECT * FROM '{t}' LIMIT 5"):
            print(row)
    except Exception as e:
        print("Erreur lecture table", t, ":", e)

conn.close()