"""
Routes d'administration (interface minimale).

- Utiliser un décorateur @admin_required pour protéger toutes les routes admin.
- Les routes de debug sont accessibles uniquement si app.debug est True.
"""
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, abort, current_app
from app.services_init import products
from pathlib import Path
import sqlite3, uuid
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

def admin_required(f):
    """Décorateur : redirige vers la page de login si l'utilisateur n'est pas admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            # rediriger vers la page de login ; conserve la cible en next si besoin
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    """Tableau de bord admin protégé. Lecture directe depuis la base pour afficher les stocks réels."""
    db = _db_path()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, price_cents, stock_qty, category, active FROM product ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    products_list = []
    for r in rows:
        products_list.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "price_cents": r[3],
            "stock_qty": r[4],
            "category": r[5],
            "active": bool(r[6])
        })

    return render_template("admin.html", products=products_list)

@admin_bp.route("/admin/product/delete", methods=["POST"])
@admin_required
def delete_product():
    """Suppression d'un produit (POST)."""
    pid = request.form.get("product_id")
    try:
        products.delete(pid)
        flash("Produit supprimé.", "success")
    except Exception as e:
        flash("Erreur suppression: " + str(e), "danger")
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/admin/dev-session")
def admin_dev_session():
    """
    Route de debug : accessible seulement en mode DEBUG et pour admin.
    Supprimer complètement en production.
    """
    if not current_app.debug:
        abort(404)
    if not session.get("is_admin"):
        return redirect(url_for("auth.login", next=request.path))
    return jsonify({k: (str(v) if not isinstance(v, (str, int, bool)) else v) for k, v in dict(session).items()})

def _db_path():
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "elegance.db"

@admin_bp.route("/admin/orders")
@admin_required
def admin_orders():
    """Liste des commandes avec tracking si disponible."""
    db = _db_path()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, status, total_cents, created_at FROM "order" ORDER BY created_at DESC')
    rows = cur.fetchall()
    orders = []
    for oid, uid, status, total_cents, created_at in rows:
        user = cur.execute("SELECT email FROM user WHERE id = ?", (uid,)).fetchone()
        delivery = cur.execute("SELECT tracking_number, status FROM delivery WHERE order_id = ?", (oid,)).fetchone()
        orders.append({
            "id": oid,
            "user_email": user[0] if user else None,
            "status": status,
            "total_cents": total_cents,
            "created_at": created_at,
            "tracking": delivery[0] if delivery else None,
            "delivery_status": delivery[1] if delivery else None
        })
    conn.close()
    return render_template("admin_orders.html", orders=orders)

@admin_bp.route("/admin/order/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    """Détail d'une commande : items / delivery / paiement."""
    db = _db_path()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    order = cur.execute('SELECT id, user_id, status, total_cents, created_at FROM "order" WHERE id = ?', (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Commande non trouvée.", "danger")
        return redirect(url_for("admin.admin_orders"))
    items = cur.execute("SELECT product_id, quantity, price_cents FROM order_item WHERE order_id = ?", (order_id,)).fetchall()
    delivery = cur.execute("SELECT id, carrier, tracking_number, status, updated_at FROM delivery WHERE order_id = ?", (order_id,)).fetchone()
    payment = cur.execute("SELECT id, provider, provider_ref, succeeded, amount_cents FROM payment WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return render_template("admin_order_detail.html", order=order, items=items, delivery=delivery, payment=payment)

@admin_bp.route("/admin/order/ship", methods=["POST"])
@admin_required
def admin_order_ship():
    """Marquer une commande comme expédiée ; crée/complète la ligne delivery avec tracking."""
    order_id = request.form.get("order_id")
    if not order_id:
        flash("Order id manquant.", "danger")
        return redirect(url_for("admin.admin_orders"))
    db = _db_path()
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    # generate tracking
    tracking = "TRK" + uuid.uuid4().hex[:12].upper()
    now = datetime.utcnow().isoformat()
    # update/create delivery row
    d = cur.execute("SELECT id FROM delivery WHERE order_id = ?", (order_id,)).fetchone()
    if d:
        cur.execute("UPDATE delivery SET tracking_number = ?, status = ?, updated_at = ? WHERE id = ?", (tracking, "shipped", now, d[0]))
    else:
        cur.execute("INSERT INTO delivery (order_id, carrier, tracking_number, status, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (order_id, "Transporteur", tracking, "shipped", now))
    # update order status
    cur.execute('UPDATE "order" SET status = ? WHERE id = ?', ("EXPEDIEE", order_id))
    conn.commit()
    conn.close()
    flash(f"Commande {order_id} marquée expédiée (tracking {tracking}).", "success")
    return redirect(url_for("admin.admin_orders"))