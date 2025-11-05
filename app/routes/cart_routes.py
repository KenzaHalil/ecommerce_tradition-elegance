from flask import Blueprint, current_app, redirect, url_for, render_template, request, flash, session
from app.models import Product

cart_bp = Blueprint("cart", __name__)

def _session_add(product_id, qty):
    cart = session.get("cart", {})
    cart[product_id] = cart.get(product_id, 0) + qty
    if cart[product_id] <= 0:
        cart.pop(product_id, None)
    session["cart"] = cart

def _session_view():
    cart = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = None
        price_cents = 0
        try:
            # essaie SQLAlchemy / fallback
            p = Product.query.get(pid)
            if p:
                price_cents = getattr(p, "price_cents", 0)
        except Exception:
            # Product peut être un dict/objet d'un autre service
            try:
                # si Product est un repository/dict
                p = Product.get(pid)  # silent try
            except Exception:
                p = None
        items.append({
            "product_id": pid,
            "product": p or {"id": pid, "name": pid, "price_cents": price_cents},
            "quantity": qty
        })
        total += (price_cents or 0) * qty
    return items, total

@cart_bp.route("/cart/add/<product_id>", methods=["POST"])
def add_to_cart(product_id):
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")
    try:
        qty = int(request.form.get("qty", 1))
    except Exception:
        qty = 1

    # if service available and supports add -> use it, otherwise fallback to session
    used_service = False
    if cart_svc and hasattr(cart_svc, "add"):
        try:
            # Attempt service add
            cart_svc.add(product_id, qty)
            used_service = True
            # verify service actually persisted the item (best-effort)
            try:
                items, total = cart_svc.view() if hasattr(cart_svc, "view") else (None, None)
                # if view returns empty and session already had the item, fall back
                if items is not None:
                    found = any((it.get("product_id") == product_id) or (getattr(getattr(it, "product", None), "id", None) == product_id) for it in items)
                    if not found:
                        # fallback to session if service didn't persist
                        _session_add(product_id, qty)
                        flash("Produit ajouté au panier (session fallback après échec du service).", "warning")
                        return redirect(request.referrer or url_for("catalogue.catalogue"))
                # otherwise consider success
                flash("Produit ajouté au panier.", "success")
            except Exception:
                # if view check fails, fallback to session to be safe
                current_app.logger.exception("cart.view verification failed; using session fallback")
                _session_add(product_id, qty)
                flash("Produit ajouté au panier (session fallback).", "warning")
        except Exception:
            current_app.logger.exception("cart.add failed, falling back to session")
            _session_add(product_id, qty)
            flash("Produit ajouté au panier (session fallback).", "warning")
    else:
        _session_add(product_id, qty)
        flash("Produit ajouté au panier (session).", "success")

    return redirect(request.referrer or url_for("catalogue.catalogue"))

@cart_bp.route("/cart")
def view_cart():
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")

    # prefer service view when available
    if cart_svc and hasattr(cart_svc, "view"):
        try:
            items, total_cents = cart_svc.view()
            # if service returned empty but session has items, prefer session (fallback)
            session_cart = session.get("cart", {})
            if (not items) and session_cart:
                current_app.logger.debug("cart view empty from service but session has items -> using session fallback")
                items, total_cents = _session_view()
        except Exception:
            current_app.logger.exception("cart.view failed, using session fallback")
            items, total_cents = _session_view()
    else:
        items, total_cents = _session_view()

    return render_template("cart.html", items=items, cart_total=(total_cents or 0)/100)

@cart_bp.route("/cart/remove/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")
    if cart_svc and hasattr(cart_svc, "remove"):
        try:
            cart_svc.remove(product_id, 0)
            flash("Produit supprimé du panier.", "info")
        except Exception:
            current_app.logger.exception("cart.remove failed, using session fallback")
            cart = session.get("cart", {})
            cart.pop(product_id, None)
            session["cart"] = cart
            flash("Produit supprimé du panier (session).", "info")
    else:
        cart = session.get("cart", {})
        cart.pop(product_id, None)
        session["cart"] = cart
        flash("Produit supprimé du panier (session).", "info")
    return redirect(url_for("cart.view_cart"))

@cart_bp.route("/cart/update", methods=["POST"])
@cart_bp.route("/cart/update/<product_id>", methods=["POST"])
def update_cart(product_id=None):
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")

    # helper to set qty in session
    def _session_set(pid, qty):
        cart = session.get("cart", {})
        if qty <= 0:
            cart.pop(pid, None)
        else:
            cart[pid] = qty
        session["cart"] = cart

    # single-item update (template posts to cart.update_cart with product_id)
    if product_id:
        try:
            qty = int(request.form.get("qty", request.form.get("quantity", 0)))
        except Exception:
            qty = 0

        if cart_svc and hasattr(cart_svc, "view"):
            # try direct set if available
            if hasattr(cart_svc, "set_quantity"):
                try:
                    cart_svc.set_quantity(product_id, qty)
                    flash("Panier mis à jour.", "success")
                    return redirect(url_for("cart.view_cart"))
                except Exception:
                    current_app.logger.exception("cart.set_quantity failed")
            # otherwise compute delta and call add/remove if present
            try:
                items, _ = cart_svc.view()
                current = 0
                for it in items:
                    # support dict or object shapes
                    pid = None
                    curq = None
                    if isinstance(it, dict):
                        pid = str(it.get("product_id") or (it.get("product") and it["product"].get("id")))
                        curq = int(it.get("quantity") or 0)
                    else:
                        prod = getattr(it, "product", None)
                        pid = str(getattr(prod, "id", None) if prod else getattr(it, "product_id", None))
                        curq = int(getattr(it, "quantity", 0) or 0)
                    if pid == str(product_id):
                        current = curq
                        break
                delta = qty - current
                if delta > 0 and hasattr(cart_svc, "add"):
                    cart_svc.add(product_id, delta)
                elif delta < 0 and hasattr(cart_svc, "remove"):
                    cart_svc.remove(product_id, -delta)
                else:
                    # fallback to session if service can't handle
                    _session_set(product_id, qty)
                flash("Panier mis à jour.", "success")
                return redirect(url_for("cart.view_cart"))
            except Exception:
                current_app.logger.exception("cart.update single-item failed, using session fallback")
                _session_set(product_id, qty)
                flash("Panier mis à jour (session fallback).", "warning")
                return redirect(url_for("cart.view_cart"))
        else:
            # session fallback
            _session_set(product_id, qty)
            flash("Panier mis à jour.", "success")
            return redirect(url_for("cart.view_cart"))

    # full-cart update (quantities[...] form keys)
    if not cart_svc or not hasattr(cart_svc, "view"):
        new_cart = {}
        for key, val in request.form.items():
            if key.startswith("quantities[") and key.endswith("]"):
                pid = key[len("quantities["):-1]
                try:
                    q = int(val)
                except Exception:
                    q = 0
                if q > 0:
                    new_cart[pid] = q
        session["cart"] = new_cart
        flash("Panier mis à jour.", "success")
        return redirect(url_for("cart.view_cart"))

    # delegate full update to service if possible (best-effort)
    try:
        current_items, _ = cart_svc.view()
    except Exception:
        current_items = []
    current_map = {}
    for it in current_items:
        if isinstance(it, dict):
            pid = it.get("product_id") or (it.get("product") and it["product"].get("id"))
            qty = int(it.get("quantity") or 0)
        else:
            prod = getattr(it, "product", None)
            pid = getattr(prod, "id", None) if prod else getattr(it, "product_id", None)
            qty = int(getattr(it, "quantity", 0) or 0)
        if pid is not None:
            current_map[str(pid)] = qty

    for key, val in request.form.items():
        if key.startswith("quantities[") and key.endswith("]"):
            pid = key[len("quantities["):-1]
            try:
                qty = int(val)
            except Exception:
                continue
            delta = qty - current_map.get(str(pid), 0)
            if delta > 0 and hasattr(cart_svc, "add"):
                cart_svc.add(pid, delta)
            elif delta < 0 and hasattr(cart_svc, "remove"):
                cart_svc.remove(pid, -delta)

    flash("Panier mis à jour.", "success")
    return redirect(url_for("cart.view_cart"))