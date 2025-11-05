import subprocess, sys, sqlite3, textwrap
from pathlib import Path
import os

SCRIPT = textwrap.dedent("""\
    import sqlite3, os
    from uuid import uuid4
    from datetime import datetime
    DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
    def gen_tracking(): return "TRK" + uuid4().hex[:8].upper()
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id FROM 'order' WHERE paid_at IS NOT NULL AND id NOT IN (SELECT order_id FROM delivery)")
    orders = [r[0] for r in cur.fetchall()]
    for oid in orders:
        cur.execute("INSERT INTO delivery (order_id, carrier, tracking_number, address, status, updated_at) VALUES (?,?,?,?,?,?)",
                    (oid, "Carrier", gen_tracking(), None, "pending", datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
""")

def _make_db(path, orders):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE "order" (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        status VARCHAR(20),
        total_cents INTEGER,
        created_at DATETIME,
        payment_id INTEGER,
        invoice_id INTEGER,
        validated_at DATETIME,
        paid_at DATETIME,
        shipped_at DATETIME,
        delivered_at DATETIME,
        cancelled_at DATETIME,
        refunded_at DATETIME
    )""")
    cur.execute("""CREATE TABLE delivery (
        id INTEGER PRIMARY KEY,
        order_id INTEGER,
        carrier VARCHAR(50),
        tracking_number VARCHAR(128),
        address TEXT,
        status VARCHAR(30),
        tracking_url TEXT,
        shipped_at TEXT,
        delivered_at TEXT,
        updated_at TEXT
    )""")
    for oid, paid_at in orders:
        cur.execute("INSERT INTO 'order'(id, paid_at) VALUES (?,?)", (oid, paid_at))
    conn.commit()
    conn.close()

def test_create_missing_deliveries_script(tmp_path):
    proj = tmp_path / "proj"
    scripts = proj / "scripts"
    scripts.mkdir(parents=True)
    # write script
    script_file = scripts / "create_missing_deliveries.py"
    script_file.write_text(SCRIPT, encoding="utf8")

    db = proj / "elegance.db"
    orders = [(1, "2025-10-30 10:00:00"), (2, None), (3, "2025-10-30 11:00:00")]
    _make_db(str(db), orders)

    proc = subprocess.run([sys.executable, str(script_file)], cwd=str(scripts), capture_output=True, text=True)
    assert proc.returncode == 0

    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT order_id, tracking_number FROM delivery ORDER BY order_id")
    rows = cur.fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] == 1 and rows[1][0] == 3
    assert rows[0][1].startswith("TRK")