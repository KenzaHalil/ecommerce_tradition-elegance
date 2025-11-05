from flask import Blueprint, current_app, redirect, url_for, render_template, request, flash

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/cart/add/<product_id>", methods=["POST"])
def add_to_cart(product_id):
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
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    items, total_cents = cart_svc.view()
    return render_template("cart.html", items=items, cart_total=total_cents/100)

@cart_bp.route("/cart/remove/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    services = current_app.extensions["services"]
    cart_svc = services["cart"]
    cart_svc.remove(product_id, 0)
    flash("Produit supprimé du panier.", "info")
    return redirect(url_for("cart.view_cart"))

@cart_bp.route("/cart/update", methods=["POST"])
def update_cart():
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