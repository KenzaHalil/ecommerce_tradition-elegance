import sqlite3, os
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'elegance.db')
conn = sqlite3.connect(db)
print("PRAGMA table_info(cart_item):")
for row in conn.execute("PRAGMA table_info(cart_item)"):
    print(row)
print("\nContenu cart_item (id, product_id, quantity, size):")
for row in conn.execute("SELECT id, product_id, quantity, size FROM cart_item"):
    print(row)
conn.close()