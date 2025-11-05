import sqlite3, os
from uuid import uuid4
from datetime import datetime

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
if not os.path.exists(DB):
    print("DB introuvable:", DB); raise SystemExit(1)

def gen_tracking():
    return "TRK" + uuid4().hex[:12].upper()

conn = sqlite3.connect(DB)
cur = conn.cursor()

# trouver les orders payées sans livraison
cur.execute("""
SELECT id FROM 'order'
WHERE paid_at IS NOT NULL
AND id NOT IN (SELECT order_id FROM delivery)
""")
orders = [r[0] for r in cur.fetchall()]
print("Orders à traiter:", orders)

for oid in orders:
    tn = gen_tracking()
    now = datetime.utcnow().isoformat()
    cur.execute("""
    INSERT INTO delivery (order_id, carrier, tracking_number, address, status, updated_at)
    VALUES (?,?,?,?,?,?)
    """, (oid, "Transporteur", tn, None, "pending", now))
    print("Créée delivery pour order", oid, "->", tn)

conn.commit()
conn.close()
print("Terminé.")