import sqlite3, os, sys
if len(sys.argv) < 2:
    print("Usage: python show_product.py <product_id>")
    sys.exit(1)
pid = sys.argv[1]
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT id, name, price_cents, stock_qty, active FROM product WHERE id = ?", (pid,))
row = cur.fetchone()
if row:
    print("id, name, price_cents, stock_qty, active")
    print(row)
else:
    print("Produit non trouvé:", pid)
conn.close()