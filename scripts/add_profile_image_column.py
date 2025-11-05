import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "elegance.db"

if not DB_PATH.exists():
    print("Fichier DB introuvable :", DB_PATH)
    sys.exit(1)

conn = None
try:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('user')")
    cols = [row[1] for row in cur.fetchall()]
    if "profile_image" in cols:
        print("La colonne 'profile_image' existe déjà.")
    else:
        print("Ajout de la colonne 'profile_image' à la table user...")
        cur.execute("ALTER TABLE user ADD COLUMN profile_image TEXT DEFAULT NULL")
        conn.commit()
        print("Colonne ajoutée.")
except sqlite3.OperationalError as e:
    print("Erreur SQLite :", e)
finally:
    if conn:
        conn.close()