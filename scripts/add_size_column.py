import sqlite3, os

db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

cols = [r[1] for r in conn.execute("PRAGMA table_info(cart_item)").fetchall()]
if "size" in cols:
    print("La colonne 'size' existe déjà.")
else:
    print("Ajout de la colonne 'size' (valeur par défaut 'S')...")
    cur.execute("ALTER TABLE cart_item ADD COLUMN size VARCHAR(10)")
    cur.execute("UPDATE cart_item SET size = 'S' WHERE size IS NULL")
    conn.commit()
    print("Terminé.")

print("\nPRAGMA table_info(cart_item):")
for row in conn.execute("PRAGMA table_info(cart_item)"):
    print(row)

print("\nContenu cart_item (id, product_id, quantity, size) :")
for row in conn.execute("SELECT id, product_id, quantity, size FROM cart_item"):
    print(row)

conn.close()