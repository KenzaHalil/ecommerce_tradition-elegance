import sqlite3, os, sys

db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
if not os.path.exists(db):
    print("DB introuvable:", db); raise SystemExit(1)

q = sys.argv[1] if len(sys.argv) > 1 else None

conn = sqlite3.connect(db)
cur = conn.cursor()

cols = ["id","order_id","carrier","tracking_number","status","shipped_at","delivered_at","updated_at"]
print(" | ".join(cols))
if q:
    # si q est un entier on essaye order_id, sinon tracking_number
    try:
        cur.execute("SELECT id,order_id,carrier,tracking_number,status,shipped_at,delivered_at,updated_at FROM delivery WHERE order_id=? ORDER BY id DESC LIMIT 100", (int(q),))
    except ValueError:
        cur.execute("SELECT id,order_id,carrier,tracking_number,status,shipped_at,delivered_at,updated_at FROM delivery WHERE tracking_number LIKE ? ORDER BY id DESC LIMIT 100", (f"%{q}%",))
else:
    cur.execute("SELECT id,order_id,carrier,tracking_number,status,shipped_at,delivered_at,updated_at FROM delivery ORDER BY id DESC LIMIT 200")

for row in cur.fetchall():
    print(" | ".join([str(x) if x is not None else "-" for x in row]))

conn.close()