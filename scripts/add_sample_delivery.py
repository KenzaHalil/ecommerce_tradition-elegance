import sqlite3, os
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("INSERT INTO delivery (order_id, carrier, tracking_number, address, status, tracking_url, shipped_at, delivered_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (1, "La Poste", "TEST123456", "Rue Exemple", "shipped", "https://tracking.example/TEST123456", "2025-10-01", None, "2025-10-01"))
conn.commit()
print("Inserted sample tracking TEST123456")
conn.close()