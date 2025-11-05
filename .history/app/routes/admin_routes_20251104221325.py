"""
Routes d'administration.

But:
- Ce fichier expose un tableau de bord admin simple.
- Le contrôle d'accès repose sur la clé de session 'is_admin' (approche minimale pour dev).
- En production, remplacer par un système d'authentification/autorisation robuste
  (decorator @admin_required, vérification de token/session côté serveur, journalisation, CSRF, etc.).
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

    - Si l'utilisateur n'est pas admin, redirige vers la page de connexion.
    - Sinon, rend le template 'admin.html' en fournissant la liste complète des produits.
    """
    if not admin_required():
        # Redirection pour les utilisateurs non autorisés
        return redirect(url_for("auth.login"))
    # Récupère tous les produits via le service centralisé et affiche la page admin
    return render_template("admin.html", products=products.list_all())

@admin_bp.route("/admin/dev-session")
def admin_dev_session():
    """Dev only: affiche le contenu de la session pour debug."""
    return jsonify({k: (str(v) if not isinstance(v, (str,int,bool)) else v) for k,v in dict(session).items()})

@admin_bp.route("/admin/product/edit/<product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not admin_required():
        return redirect(url_for("auth.login"))
    # try to load product via service
    try:
        prod = products.get(product_id)
    except Exception:
        prod = None
    if request.method == "POST":
        # récupérer champs du form et sauvegarder
        name = request.form.get("name")
        price = request.form.get("price_cents")
        stock = request.form.get("stock_qty")
        # appeler ton service pour update (adapter selon API)
        try:
            products.update(product_id, name=name, price_cents=int(price), stock_qty=int(stock))
            flash("Produit mis à jour.", "success")
            return redirect(url_for("admin.admin_dashboard"))
        except Exception as e:
            flash("Erreur mise à jour: " + str(e), "danger")
    return render_template("admin_edit_product.html", product=prod)

@admin_bp.route("/admin/product/delete", methods=["POST"])
def delete_product():
    if not admin_required():
        return redirect(url_for("auth.login"))
    pid = request.form.get("product_id")
    try:
        products.delete(pid)
        flash("Produit supprimé.", "success")
    except Exception as e:
        flash("Erreur suppression: " + str(e), "danger")
    return redirect(url_for("admin.admin_dashboard"))