import sqlite3, os
db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elegance.db")
conn = sqlite3.connect(db)
for row in conn.execute('PRAGMA table_info("order")'):
    print(row)
conn.close()