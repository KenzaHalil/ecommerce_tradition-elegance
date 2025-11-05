"""
Supprime un utilisateur et les données liées (orders, payments, deliveries, cart, messages).
Usage:
  .\venv\Scripts\Activate.ps1
  python .\scripts\delete_user.py admin@example.com
"""
import sqlite3, os, sys, shutil

PROJECT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(PROJECT, "elegance.db")

if not os.path.exists(DB):
    print("DB introuvable:", DB); sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python delete_user.py email@example.com"); sys.exit(1)

email = sys.argv[1]

# backup DB
bak = DB + ".bak"
shutil.copy2(DB, bak)
print("Sauvegarde créée :", bak)

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# find user
cur.execute("SELECT id,email FROM user WHERE email = ?", (email,))
row = cur.fetchone()
if not row:
    print("Utilisateur introuvable :", email)
    conn.close()
    sys.exit(1)

user_id = row[0]
print("Utilisateur trouvé id =", user_id, "email =", row[1])

# collect related object counts for confirmation
def count(q, params=()):
    try:
        return cur.execute(q, params).fetchone()[0]
    except Exception:
        return 0

order_ids = [r[0] for r in cur.execute('SELECT id FROM "order" WHERE user_id = ?', (user_id,)).fetchall()]
print("Données liées :")
print(" - commandes:", count('SELECT COUNT(*) FROM "order" WHERE user_id = ?', (user_id,)))
print(" - order_item total:", count('SELECT COUNT(*) FROM order_item WHERE order_id IN (' + (','.join('?'*len(order_ids)) if order_ids else 'NULL') + ')', tuple(order_ids) if order_ids else ()))
print(" - deliveries:", count('SELECT COUNT(*) FROM delivery WHERE order_id IN (' + (','.join('?'*len(order_ids)) if order_ids else 'NULL') + ')', tuple(order_ids) if order_ids else ()))
print(" - payments (par user):", count('SELECT COUNT(*) FROM payment WHERE user_id = ?', (user_id,)))
print(" - invoices (par user):", count('SELECT COUNT(*) FROM invoice WHERE user_id = ?', (user_id,)))
print(" - cart:", count('SELECT COUNT(*) FROM cart WHERE user_id = ?', (user_id,)))
print(" - cart_item:", count('SELECT COUNT(*) FROM cart_item WHERE cart_user_id = ?', (user_id,)))
print(" - message_thread:", count('SELECT COUNT(*) FROM message_thread WHERE user_id = ?', (user_id,)))
print(" - messages (author):", count('SELECT COUNT(*) FROM message WHERE author_user_id = ?', (user_id,)))

ok = input("Confirmer suppression de l'utilisateur et des données listées ? (oui/non) : ").strip().lower()
if ok not in ("o","oui","y","yes"):
    print("Abandon.")
    conn.close()
    sys.exit(0)

# delete dependent rows in safe order
try:
    if order_ids:
        ph = ",".join("?"*len(order_ids))
        cur.execute(f"DELETE FROM delivery WHERE order_id IN ({ph})", tuple(order_ids))
        cur.execute(f"DELETE FROM order_item WHERE order_id IN ({ph})", tuple(order_ids))
        cur.execute(f"DELETE FROM invoice WHERE order_id IN ({ph})", tuple(order_ids))
        cur.execute(f"DELETE FROM payment WHERE order_id IN ({ph})", tuple(order_ids))
    # payments directly linked to user
    cur.execute("DELETE FROM payment WHERE user_id = ?", (user_id,))
    # orders
    cur.execute('DELETE FROM "order" WHERE user_id = ?', (user_id,))
    # invoices linked to user (if any)
    cur.execute('DELETE FROM invoice WHERE user_id = ?', (user_id,))
    # cart items then cart
    cur.execute("DELETE FROM cart_item WHERE cart_user_id = ?", (user_id,))
    cur.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    # messages and threads
    cur.execute("DELETE FROM message WHERE author_user_id = ?", (user_id,))
    cur.execute("DELETE FROM message_thread WHERE user_id = ?", (user_id,))
    # finally user
    cur.execute("DELETE FROM user WHERE id = ?", (user_id,))
    conn.commit()
    print("Suppression effectuée. Vérifications rapides :")
    print(" - user exists:", cur.execute("SELECT COUNT(*) FROM user WHERE id = ?", (user_id,)).fetchone()[0])
    print(" - orders remaining for user:", cur.execute('SELECT COUNT(*) FROM "order" WHERE user_id = ?', (user_id,)).fetchone()[0])
except Exception as e:
    conn.rollback()
    print("Erreur, rollback effectué :", e)
finally:
    conn.close()

print("Terminé. Si erreur, restaure la sauvegarde :", bak)