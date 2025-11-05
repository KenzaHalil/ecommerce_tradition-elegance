import sqlite3, os

db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
).fetchall()]

print("Tables:", tables)
for t in tables:
    print("\n---", t, "---")
    # utiliser des guillemets pour gérer les noms réservés / contenant des caractères
    try:
        for c in cur.execute(f'PRAGMA table_info("{t}")'):
            print("  col:", c)
    except Exception as e:
        print("  PRAGMA failed:", e)
    try:
        rows = cur.execute(f'SELECT * FROM "{t}" LIMIT 5').fetchall()
        print("  rows (up to 5):")
        for r in rows:
            print("   ", r)
    except Exception as e:
        print("  cannot read rows:", e)

conn.close()