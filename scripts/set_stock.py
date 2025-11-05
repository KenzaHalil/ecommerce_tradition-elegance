import sqlite3, os, sys

def usage():
    print("Usage:")
    print("  python set_stock.py <product_id|all> <new_qty>")
    print("Examples:")
    print("  python set_stock.py 42 30      # set product id 42 to 30")
    print("  python set_stock.py all 30     # set ALL products to 30")
    sys.exit(1)

if len(sys.argv) < 3:
    usage()

pid = sys.argv[1]
try:
    qty = int(sys.argv[2])
except ValueError:
    print("new_qty must be an integer")
    sys.exit(1)

db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
if not os.path.exists(db):
    print(f"Database not found: {db}")
    sys.exit(1)

conn = sqlite3.connect(db)
cur = conn.cursor()

# detect table that likely contains products
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
candidates = ["product", "products", "item", "items"]
table = next((t for t in candidates if t in tables), None)
if not table:
    # try to find a table with stock_qty column
    for t in tables:
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        if "stock_qty" in cols or "stock" in cols:
            table = t
            break

if not table:
    print("No product table found (looked for 'product'/'products' or column 'stock_qty'). Aborting.")
    conn.close()
    sys.exit(1)

print("Using table:", table)

if pid.lower() in ("all", "*"):
    cur.execute(f"UPDATE {table} SET stock_qty = ?", (qty,))
    conn.commit()
    print(f"Updated ALL products -> stock_qty = {qty} (rows affected: {cur.rowcount})")
else:
    # try numeric id first
    try:
        int_pid = int(pid)
        cur.execute(f"UPDATE {table} SET stock_qty = ? WHERE id = ?", (qty, int_pid))
    except Exception:
        cur.execute(f"UPDATE {table} SET stock_qty = ? WHERE id = ?", (qty, pid))
    conn.commit()
    print(f"Updated {pid} -> stock_qty = {qty} (rows affected: {cur.rowcount})")

# summary
cnt = cur.execute(f"SELECT COUNT(*) FROM {table} WHERE stock_qty = ?", (qty,)).fetchone()[0]
print(f"Rows with stock_qty={qty}: {cnt}")

conn.close()