from pathlib import Path
import sqlite3
import shutil

PROJECT = Path(__file__).resolve().parents[1]
DB = PROJECT / "elegance.db"
BACKUP = PROJECT / f"elegance.db.bak"

if not DB.exists():
    print("DB introuvable:", DB); raise SystemExit(1)

# backup
if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)
    print("Backup créé:", BACKUP)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

def has_column(table: str, column: str) -> bool:
    cur.execute("PRAGMA table_info(%s)" % ("'"+table+"'"))
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

def add_column_if_missing(table: str, col_sql: str):
    col_name = col_sql.split()[0]
    if not has_column(table, col_name):
        sql = f"ALTER TABLE {table} ADD COLUMN {col_sql}"
        print("Ajout colonne:", table, col_sql)
        cur.execute(sql)
    else:
        print("Colonne existe:", table, col_name)

# product.active
add_column_if_missing("product", "active INTEGER DEFAULT 1")

# user.is_admin + user.address
add_column_if_missing("user", "is_admin INTEGER DEFAULT 0")
add_column_if_missing("user", "address TEXT")

# order: link to payment/invoice + timestamps
add_column_if_missing('"order"', "payment_id INTEGER")
add_column_if_missing('"order"', "invoice_id INTEGER")
add_column_if_missing('"order"', "validated_at DATETIME")
add_column_if_missing('"order"', "paid_at DATETIME")
add_column_if_missing('"order"', "shipped_at DATETIME")
add_column_if_missing('"order"', "delivered_at DATETIME")
add_column_if_missing('"order"', "cancelled_at DATETIME")
add_column_if_missing('"order"', "refunded_at DATETIME")

conn.commit()
conn.close()
print("Migrations simples appliquées.")