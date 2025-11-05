import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "elegance.db"
if not db.exists():
    print("Fichier DB introuvable :", db)
    raise SystemExit(1)

conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute("PRAGMA table_info('user')")
rows = cur.fetchall()
cols = [r[1] for r in rows]
print("Colonnes de la table user :", cols)
for r in rows:
    # r format: (cid, name, type, notnull, dflt_value, pk)
    print(f" - {r[1]}  type={r[2]}  notnull={r[3]}  default={r[4]}  pk={r[5]}")
conn.close()