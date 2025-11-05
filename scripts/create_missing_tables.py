import sqlite3
from pathlib import Path
DB = Path(__file__).resolve().parents[1] / "elegance.db"
bak = DB.with_suffix(".bak.db")
if DB.exists():
    DB.replace(bak)  # sauvegarde avant modification
    bak.replace(DB)  # restore original name (simple safe copy)
# NOTE: if replace above fails on your Windows, make a manual copy before running

sql = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cart (
    user_id INTEGER NOT NULL PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS cart_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_user_id INTEGER NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY(cart_user_id) REFERENCES cart(user_id),
    FOREIGN KEY(product_id) REFERENCES product(id)
);

CREATE TABLE IF NOT EXISTS invoice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    user_id INTEGER,
    total_cents INTEGER,
    issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES "order"(id),
    FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS invoice_line (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id VARCHAR(50),
    name VARCHAR(255),
    unit_price_cents INTEGER,
    quantity INTEGER,
    line_total_cents INTEGER,
    FOREIGN KEY(invoice_id) REFERENCES invoice(id),
    FOREIGN KEY(product_id) REFERENCES product(id)
);

CREATE TABLE IF NOT EXISTS payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    user_id INTEGER,
    amount_cents INTEGER,
    provider VARCHAR(50),
    provider_ref VARCHAR(128),
    succeeded INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES "order"(id),
    FOREIGN KEY(user_id) REFERENCES user(id)
);

CREATE TABLE IF NOT EXISTS delivery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    carrier VARCHAR(50),
    tracking_number VARCHAR(128),
    address TEXT,
    status VARCHAR(30),
    FOREIGN KEY(order_id) REFERENCES "order"(id)
);

CREATE TABLE IF NOT EXISTS message_thread (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_id INTEGER,
    subject VARCHAR(255),
    closed INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES user(id),
    FOREIGN KEY(order_id) REFERENCES "order"(id)
);

CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL,
    author_user_id INTEGER,
    body TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(thread_id) REFERENCES message_thread(id),
    FOREIGN KEY(author_user_id) REFERENCES user(id)
);
"""
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.executescript(sql)
conn.commit()
conn.close()
print("Tables manquantes créées (si elles n'existaient pas).")