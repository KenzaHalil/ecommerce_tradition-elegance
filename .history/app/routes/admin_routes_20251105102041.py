"""
Routes d'administration (interface minimale).

- Utiliser un décorateur @admin_required pour protéger toutes les routes admin.
- Les routes de debug sont accessibles uniquement si app.debug est True.
"""
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, abort, current_app
from app.services_init import products

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
    """Tableau de bord admin protégé."""
    return render_template("admin.html", products=products.list_all())

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