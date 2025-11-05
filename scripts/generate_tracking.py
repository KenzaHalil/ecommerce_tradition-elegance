import sqlite3, os, uuid
from datetime import datetime

PROJECT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(PROJECT, "elegance.db")

def make_tracking():
    return "TRK" + uuid.uuid4().hex[:12].upper()

if not os.path.exists(DB):
    print("DB not found:", DB); raise SystemExit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Orders without a delivery with a tracking_number
rows = cur.execute("""
SELECT id FROM "order"
WHERE id NOT IN (
  SELECT order_id FROM delivery WHERE tracking_number IS NOT NULL
)
""").fetchall()

created = 0
updated = 0
for (order_id,) in rows:
    # If a delivery row exists but tracking_number is NULL -> update it
    d = cur.execute("SELECT id, tracking_number FROM delivery WHERE order_id = ?", (order_id,)).fetchone()
    tn = make_tracking()
    now = datetime.utcnow().isoformat()
    if d:
        cur.execute("UPDATE delivery SET tracking_number = ?, status = ?, updated_at = ? WHERE id = ?", (tn, "pending", now, d[0]))
        updated += cur.rowcount
    else:
        cur.execute(
            "INSERT INTO delivery (order_id, carrier, tracking_number, status, updated_at) VALUES (?, ?, ?, ?, ?)",
            (order_id, "Transporteur", tn, "pending", now)
        )
        created += 1

conn.commit()
print(f"Created: {created}, Updated: {updated}")
conn.close()