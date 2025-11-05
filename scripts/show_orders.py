import sqlite3, os
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
print("Dernières commandes (id, user_id, total_cents, created_at):")
for row in cur.execute('SELECT id, user_id, total_cents, created_at FROM "order" ORDER BY id DESC LIMIT 10'):
    print(row)
conn.close()