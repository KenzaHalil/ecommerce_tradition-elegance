"""
Routes d'administration (interface minimale).

Notes importantes :
- Contrôle d'accès simple basé sur session['is_admin'] (développement uniquement).
- En production, remplacer par Flask-Login + rôles/permissions robustes.
- Le service `products` est attendu dans app.services_init et doit fournir list_all() et delete().
"""
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.services_init import products

admin_bp = Blueprint("admin", __name__)

def admin_required():
    """
    Retourne True si la session indique un administrateur.
    - Ne vérifie pas d'autres facteurs (CSRF, token, etc.). Strictement dev.
    """
    return session.get("is_admin")

@admin_bp.route("/admin")
def admin_dashboard():
    """
    Tableau de bord admin : liste de produits via products.list_all().
    - Si non autorisé, redirection vers la page de login.
    - Template admin.html doit exister (sinon TemplateNotFound).
    """
    if not admin_required():
        return redirect(url_for("auth.login"))
    return render_template("admin.html", products=products.list_all())

@admin_bp.route("/admin/dev-session")
def admin_dev_session():
    """
    Route de debug (dev only) pour afficher le contenu de la session.
    - Supprimer en production.
    """
    return jsonify({k: (str(v) if not isinstance(v, (str,int,bool)) else v) for k,v in dict(session).items()})

@admin_bp.route("/admin/product/delete", methods=["POST"])
def delete_product():
    """
    Suppression d'un produit depuis le tableau de bord.
    - Expose un point POST qui attend product_id dans request.form.
    - Appelle products.delete(pid) et affiche un message flash.
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