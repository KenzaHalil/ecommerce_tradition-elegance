"""
Routes liées au panier (cart) et opérations courantes.

Responsabilités :
- add_to_cart : ajouter une quantité d'un produit au panier via le service "cart".
- view_cart : afficher le panier et le total.
- remove_from_cart : suppression d'un produit (réinitialise quantité).
- update_cart : mise à jour des quantités envoyées depuis un formulaire.

Hypothèses :
- Les services sont disponibles dans current_app.extensions['services'] et exposent
  une interface attendue (cart.add, cart.view, cart.remove).
- Les éléments de cart.view() renvoient (items, total_cents) où items contient
  des objets/structs avec "product" et "quantity".
- Les templates attendent cart_total en euros (float).
"""
from flask import Blueprint, current_app, redirect, url_for, render_template, request, flash

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/cart/add/<product_id>", methods=["POST"])
def add_to_cart(product_id):
    """
    Ajoute `qty` unités du produit `product_id` au panier via le service cart.
    - Lit qty depuis request.form (fallback à 1 si invalide).
    - En cas d'erreur côté service, flash + redirection vers le catalogue.
    """
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    try:
        qty = int(request.form.get("qty", 1))
    except Exception:
        qty = 1
    try:
        cart_svc.add(product_id, qty)
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("catalogue.catalogue"))
    flash("Produit ajouté au panier.", "success")
    return redirect(url_for("catalogue.catalogue"))

@cart_bp.route("/cart")
def view_cart():
    """
    Affiche le panier.
    - Récupère items et total en centimes depuis le service cart.
    - Convertit total_cents en euros pour le template.
    """
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    items, total_cents = cart_svc.view()
    return render_template("cart.html", items=items, cart_total=total_cents/100)

@cart_bp.route("/cart/remove/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    """
    Supprime entièrement un produit du panier.
    - Ici l'appel cart_svc.remove(product_id, 0) doit retirer la ligne.
    - Utiliser POST pour éviter suppression via GET.
    """
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    cart_svc.remove(product_id, 0)
    flash("Produit supprimé du panier.", "info")
    return redirect(url_for("cart.view_cart"))

@cart_bp.route("/cart/update", methods=["POST"])
def update_cart():
    """
    Met à jour les quantités du panier depuis un formulaire avec inputs nommés
    `quantities[<product_id>]`.
    - Pour chaque champ, calcule le delta entre quantité demandée et quantité courante,
      puis appelle cart_svc.add/remove pour ajuster.
    - Avantage : délégation de la logique de persistance au service cart.
    - Limitation : recherche linéaire pour retrouver la quantité courante (acceptable pour petits paniers).
    """
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    for key, val in request.form.items():
        if key.startswith("quantities[") and key.endswith("]"):
            pid = key[len("quantities["):-1]
            try:
                qty = int(val)
            except ValueError:
                continue
            # set quantity by adjusting delta
            current_items, _ = cart_svc.view()
            current_q = 0
            for it in current_items:
                # it["product"] peut être un objet Product ; comparer sur id
                if it["product"].id == pid:
                    current_q = it["quantity"]
                    break
            delta = qty - current_q
            if delta > 0:
                cart_svc.add(pid, delta)
            elif delta < 0:
                cart_svc.remove(pid, -delta)
    flash("Panier mis à jour.", "success")
    return redirect(url_for("cart.view_cart"))