"""
Routes d'administration.

But:
- Ce fichier expose un tableau de bord admin simple.
- Le contrôle d'accès repose sur la clé de session 'is_admin' (approche minimale pour dev).
- En production, remplacer par un système d'authentification/autorisation robuste.
- Le service `products` vient de app.services_init et doit exposer une méthode list_all().
"""

from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.services_init import products

admin_bp = Blueprint("admin", __name__)

def admin_required():
    """
    Indique si l'utilisateur courant a les droits admin.
    Retourne True si la session contient 'is_admin' truthy.
    """
    return session.get("is_admin")

@admin_bp.route("/admin")
def admin_dashboard():
    """
    Vue du tableau de bord admin.
    """
    if not admin_required():
        return redirect(url_for("auth.login"))
    return render_template("admin.html", products=products.list_all())

@admin_bp.route("/admin/dev-session")
def admin_dev_session():
    """Dev only: affiche le contenu de la session pour debug."""
    return jsonify({k: (str(v) if not isinstance(v, (str,int,bool)) else v) for k,v in dict(session).items()})

@admin_bp.route("/admin/product/delete", methods=["POST"])
def delete_product():
    """
    Suppression d'un produit (POST attendu depuis le template admin).
    """
    if not admin_required():
        return redirect(url_for("auth.login"))
    pid = request.form.get("product_id")
    try:
        products.delete(pid)
        flash("Produit supprimé.", "success")
    except Exception as e:
        flash("Erreur suppression: " + str(e), "danger")
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route("/admin/product/edit/<product_id>", methods=["GET", "POST"])
def edit_product_redirect(product_id):
    """Redirige les anciennes URLs d'édition vers le dashboard (no-edit)."""
    if not admin_required():
        return redirect(url_for("auth.login"))
    flash("Édition de produit non disponible. Utilisez le tableau de bord.", "info")
    return redirect(url_for("admin.admin_dashboard"))