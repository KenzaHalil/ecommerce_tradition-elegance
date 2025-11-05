from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
import uuid

checkout_bp = Blueprint("checkout", __name__)

@checkout_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    services = current_app.extensions.get("services", {})
    order_svc = services.get("order")
    cart_svc = services.get("cart")

    # récupérer items + total (service ou session fallback)
    items, total_cents = [], 0
    if cart_svc and hasattr(cart_svc, "view"):
        try:
            items, total_cents = cart_svc.view()
        except Exception:
            items, total_cents = [], 0
    else:
        cart = session.get("cart", {})
        from app.models import Product
        for pid, qty in cart.items():
            try:
                p = Product.query.get(pid)
                price = getattr(p, "price_cents", 0) if p else 0
            except Exception:
                price = 0
            items.append({"product_id": pid, "quantity": qty, "price_cents": price})
            total_cents += (price or 0) * qty

    if request.method == "GET":
        return render_template("checkout.html", items=items, total=(total_cents or 0)/100)

    # POST -> créer la commande puis rediriger vers la page de paiement
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter pour valider la commande.", "warning")
        return redirect(url_for("auth.login"))

    if not order_svc:
        flash("Service de commande indisponible.", "danger")
        return redirect(url_for("cart.view_cart"))

    try:
        order = order_svc.create_order(user_id, items, total_cents)
    except Exception:
        current_app.logger.exception("Order creation failed")
        flash("Impossible de créer la commande.", "danger")
        return redirect(url_for("cart.view_cart"))

    # stocker info de paiement dans la session et rediriger vers la page de paiement
    session["pending_payment"] = {"order_id": order.get("id"), "amount_cents": int(total_cents or 0)}
    return redirect(url_for("checkout.pay"))

@checkout_bp.route("/checkout/pay", methods=["GET", "POST"])
def pay():
    pending = session.get("pending_payment")
    if not pending:
        flash("Aucune commande en attente de paiement.", "warning")
        return redirect(url_for("cart.view_cart"))

    if request.method == "GET":
        amount_eur = (pending.get("amount_cents", 0) or 0) / 100
        return render_template("pay.html", order_id=pending.get("order_id"), amount_eur=amount_eur)

    # POST from pay.html -> traiter paiement (simple simulation)
    card_number = request.form.get("card_number")
    # ici possibilité d'appeler payment gateway; pour dev, on simule succès
    paid = True
    if paid:
        # marquer commande payée si possible
        order_svc = current_app.extensions.get("services", {}).get("order")
        try:
            if hasattr(order_svc, "set_status"):
                order_svc.set_status(pending.get("order_id"), "PAID")
        except Exception:
            current_app.logger.exception("Failed to update order status")
        session.pop("pending_payment", None)
        session.pop("cart", None)
        flash("Paiement réussi, commande créée.", "success")
        return redirect(url_for("catalogue.catalogue"))
    else:
        flash("Paiement échoué.", "danger")
        return redirect(url_for("checkout.pay"))