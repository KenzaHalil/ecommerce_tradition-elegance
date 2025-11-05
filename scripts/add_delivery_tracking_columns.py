import sqlite3, os
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(delivery)").fetchall()]
to_add = [
    ("carrier", "TEXT"),
    ("tracking_number", "TEXT"),
    ("tracking_url", "TEXT"),
    ("status", "TEXT"),
    ("shipped_at", "TEXT"),
    ("delivered_at", "TEXT"),
    ("updated_at", "TEXT")
]

for name, typ in to_add:
    if name in cols:
        print(f"Colonne '{name}' existe déjà.")
    else:
        print(f"Ajout de la colonne '{name}'...")
        cur.execute(f"ALTER TABLE delivery ADD COLUMN {name} {typ}")
conn.commit()

print("\nPRAGMA table_info(delivery):")
for row in cur.execute("PRAGMA table_info(delivery)"):
    print(row)

conn.close()