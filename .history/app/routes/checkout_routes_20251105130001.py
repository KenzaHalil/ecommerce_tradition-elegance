from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, session
import uuid

checkout_bp = Blueprint("checkout", __name__)

def _build_items_from_session():
    from app.models import Product
    cart = session.get("cart", {}) or {}
    items = []
    total_cents = 0
    for pid, qty in cart.items():
        try:
            p = Product.query.get(pid)
            price = int(getattr(p, "price_cents", 0) or 0) if p else 0
            name = getattr(p, "name", str(pid)) if p else str(pid)
        except Exception:
            p = None
            price = 0
            name = str(pid)
        subtotal = price * int(qty)
        items.append({
            "product_id": str(pid),
            "product": {"id": str(pid), "name": name, "price_cents": price},
            "quantity": int(qty),
            "price_cents": int(price),
            "subtotal_cents": int(subtotal),
        })
        total_cents += subtotal
    return items, total_cents

def _normalize_items(items):
    """Assure que chaque item a keys: product_id, product, quantity, price_cents, subtotal_cents"""
    out = []
    total = 0
    for it in items or []:
        # support dict or object shapes
        if isinstance(it, dict):
            pid = str(it.get("product_id") or (it.get("product") and it["product"].get("id")) or it.get("id") or "")
            qty = int(it.get("quantity", 1))
            price = int(it.get("price_cents") or (it.get("product") and it["product"].get("price_cents")) or it.get("subtotal_cents",0) // max(qty,1) or 0)
            subtotal = int(it.get("subtotal_cents", price * qty))
            prod = it.get("product")
            if isinstance(prod, dict):
                prod_dict = {"id": str(prod.get("id", pid)), "name": prod.get("name", str(pid)), "price_cents": int(prod.get("price_cents", price))}
            else:
                prod_dict = {"id": pid, "name": str(prod) if prod else pid, "price_cents": price}
        else:
            # object-like
            pid = str(getattr(it, "product_id", "") or (getattr(getattr(it, "product", None), "id", None)) or getattr(it, "id", ""))
            qty = int(getattr(it, "quantity", 1) or 1)
            price = int(getattr(it, "price_cents", getattr(getattr(it, "product", None), "price_cents", 0) or 0))
            subtotal = int(getattr(it, "subtotal_cents", price * qty))
            prod = getattr(it, "product", None)
            prod_dict = {"id": str(getattr(prod, "id", pid)), "name": getattr(prod, "name", str(pid)), "price_cents": price}

        out.append({
            "product_id": pid,
            "product": prod_dict,
            "quantity": qty,
            "price_cents": price,
            "subtotal_cents": subtotal
        })
        total += subtotal
    return out, total

@checkout_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    services = current_app.extensions.get("services", {})
    order_svc = services.get("order")
    cart_svc = services.get("cart")

    # récupérer items + total (préférence service, fallback session si service vide)
    items, total_cents = [], 0
    if cart_svc and hasattr(cart_svc, "view"):
        try:
            items, total_cents = cart_svc.view()
        except Exception:
            current_app.logger.exception("cart.view failed in checkout; using session fallback")
            items, total_cents = [], 0

    # if service returned empty but session contains items, use session
    if (not items) and session.get("cart"):
        current_app.logger.debug("Using session cart in checkout because service returned empty")
        items, total_cents = _build_items_from_session()
    else:
        # normalize items returned by service or domain to ensure subtotal_cents exists
        items, total_cents = _normalize_items(items)

    if request.method == "GET":
        if not items:
            flash("Votre panier est vide. Voir le catalogue", "info")
        total_eur = (total_cents or 0) / 100
        return render_template("checkout.html", items=items, total=total_eur, total_eur=total_eur)

    # POST -> créer la commande puis rediriger vers la page de paiement
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez vous connecter pour valider la commande.", "warning")
        return redirect(url_for("auth.login"))

    if not order_svc:
        flash("Service de commande indisponible.", "danger")
        return redirect(url_for("cart.view_cart"))

    if not items:
        # final safety: rebuild from session one more time
        items, total_cents = _build_items_from_session()
        if not items:
            flash("Votre panier est vide, impossible de créer la commande.", "warning")
            return redirect(url_for("cart.view_cart"))

    try:
        order = order_svc.create_order(user_id, items, total_cents)
    except Exception as exc:
        current_app.logger.exception("Order creation failed")
        flash(f"Impossible de créer la commande. Détail: {exc}", "danger")
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
    paid = True
    if paid:
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