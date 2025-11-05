from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session

checkout_bp = Blueprint("checkout", __name__)

@checkout_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    services = current_app.extensions.get("services", {})
    order_svc = services.get("order")
    cart_svc = services.get("cart")
    payment_gateway = services.get("payment")

    # récupérer items et total (préférence service puis session fallback)
    items, total_cents = [], 0
    if cart_svc and hasattr(cart_svc, "view"):
        try:
            items, total_cents = cart_svc.view()
        except Exception:
            items, total_cents = [], 0
    else:
        # session fallback (même logique que dans cart_routes)
        cart = session.get("cart", {})
        from app.models import Product
        for pid, qty in cart.items():
            try:
                p = Product.query.get(pid)
                price = getattr(p, "price_cents", 0) if p else 0
            except Exception:
                p = None
                price = 0
            items.append({"product_id": pid, "quantity": qty, "price_cents": price})
            total_cents += (price or 0) * qty

    if request.method == "GET":
        return render_template("checkout.html", items=items, total=(total_cents or 0)/100)

    # POST -> créer la commande et tenter le paiement (simulé si pas de gateway)
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter pour valider la commande.", "warning")
        return redirect(url_for("auth.login"))

    if not order_svc:
        flash("Service de commande indisponible.", "danger")
        return redirect(url_for("cart.view_cart"))

    # create order (service peut être domaine réel ou dev)
    try:
        order = None
        # ordre attendu : create_order(user_id, items, total_cents)
        if hasattr(order_svc, "create_order"):
            order = order_svc.create_order(user_id, items, total_cents)
        else:
            # fallback minimal
            order = {"id": "dev-"+str(uuid.uuid4()), "user_id": user_id, "items": items, "total_cents": total_cents, "status": "PENDING"}
    except Exception as e:
        current_app.logger.exception("Order creation failed")
        flash("Impossible de créer la commande.", "danger")
        return redirect(url_for("cart.view_cart"))

    # simulate / call payment
    paid = False
    try:
        if payment_gateway and hasattr(payment_gateway, "charge"):
            # API hypothétique : charge(amount_cents, description, order_id, user_id)
            payment_gateway.charge(total_cents, f"Order {order.get('id')}", order.get("id"), user_id)
            paid = True
        else:
            # simulate payment success in dev
            paid = True
    except Exception:
        current_app.logger.exception("Payment failed")
        paid = False

    # update order status if possible
    try:
        if paid and hasattr(order_svc, "set_status"):
            order_svc.set_status(order.get("id"), "PAID")
        elif paid and isinstance(order, dict):
            order["status"] = "PAID"
    except Exception:
        current_app.logger.exception("Order status update failed")

    # clear session cart on success
    if paid:
        session.pop("cart", None)
        flash("Paiement réussi — commande créée.", "success")
        return redirect(url_for("order.detail", order_id=order.get("id")) if "order" in current_app.view_functions else url_for("catalogue.catalogue"))
    else:
        flash("Le paiement a échoué.", "danger")
        return redirect(url_for("cart.view_cart"))