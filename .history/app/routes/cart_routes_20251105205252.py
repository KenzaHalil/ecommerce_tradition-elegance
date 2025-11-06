from flask import Blueprint, current_app, redirect, url_for, render_template, request, flash, session
from app.models import Product
from app.auth_helpers import login_required

cart_bp = Blueprint("cart", __name__)

# Helper: add quantity to session cart (creates cart if absent).
# - product_id: string id of the product
# - qty: integer delta to add (can be negative)
def _session_add(product_id, qty):
    cart = session.get("cart", {})
    cart[product_id] = cart.get(product_id, 0) + qty
    # If quantity becomes <= 0 remove the product from the cart
    if cart[product_id] <= 0:
        cart.pop(product_id, None)
    session["cart"] = cart

# Helper: build a view of the session cart for templates
# Returns: (items, total_in_cents)
# - items: list of dict { product_id, product, quantity }
# - product might be a SQLAlchemy object or a fallback dict with minimal fields
def _session_view():
    cart = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = None
        price_cents = 0
        try:
            # Prefer SQLAlchemy Product model if available
            p = Product.query.get(pid)
            if p:
                price_cents = getattr(p, "price_cents", 0)
        except Exception:
            # If Product is a repository or different shape, try a generic get method
            try:
                p = Product.get(pid)  # best-effort, silent
            except Exception:
                p = None
        # Normalize item shape for templates
        items.append({
            "product_id": pid,
            "product": p or {"id": pid, "name": pid, "price_cents": price_cents},
            "quantity": qty
        })
        total += (price_cents or 0) * qty
    return items, total

@cart_bp.route("/cart/add/<product_id>", methods=["POST"])
@login_required()
def add_to_cart(product_id):
    # Ensure user is authenticated (explicit check, compatible si le décorateur n'est pas actif)
    if session.get("user_id") is None:
        flash("Connectez‑vous pour ajouter des produits au panier.", "warning")
        return redirect(url_for("auth.login", next=request.referrer or request.url))
    """
    Add product to cart.
    - Prefer using a cart service if available (app.extensions['services']['cart'])
    - If service fails or is absent, fallback to session cart.
    - After adding, redirect back to referrer or catalogue.
    """
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")
    try:
        qty = int(request.form.get("qty", 1))
    except Exception:
        qty = 1

    # Try to use the cart service's add method if present.
    if cart_svc and hasattr(cart_svc, "add"):
        try:
            cart_svc.add(product_id, qty)
            # Verify service persisted the item (best-effort).
            try:
                items, total = cart_svc.view() if hasattr(cart_svc, "view") else (None, None)
                if items is not None:
                    found = any(
                        (it.get("product_id") == product_id) or
                        (getattr(getattr(it, "product", None), "id", None) == product_id)
                        for it in items
                    )
                    if not found:
                        # Service didn't persist -> fallback to session
                        _session_add(product_id, qty)
                        flash("Produit ajouté au panier (session fallback après échec du service).", "warning")
                        return redirect(request.referrer or url_for("catalogue.catalogue"))
                flash("Produit ajouté au panier.", "success")
            except Exception:
                # If verification fails, fallback to session for reliability
                current_app.logger.exception("cart.view verification failed; using session fallback")
                _session_add(product_id, qty)
                flash("Produit ajouté au panier (session fallback).", "warning")
        except Exception:
            current_app.logger.exception("cart.add failed, falling back to session")
            _session_add(product_id, qty)
            flash("Produit ajouté au panier (session fallback).", "warning")
    else:
        # No service available: use session
        _session_add(product_id, qty)
        flash("Produit ajouté au panier.", "success")

    return redirect(request.referrer or url_for("catalogue.catalogue"))

@cart_bp.route("/cart")
def view_cart():
    # Require login to view the cart
    if session.get("user_id") is None:
        flash("Connectez‑vous pour voir votre panier.", "warning")
        return redirect(url_for("auth.login", next=request.url))
    """
    Show the cart page.
    - Prefer cart service view() if available.
    - If the service returns empty but the session has items, prefer the session (fallback).
    - Render cart.html with items and cart_total (in euros).
    """
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")

    # Prefer service view when available
    if cart_svc and hasattr(cart_svc, "view"):
        try:
            items, total_cents = cart_svc.view()
            # If service returned nothing but session has items, use session data (safer for the user)
            session_cart = session.get("cart", {})
            if (not items) and session_cart:
                current_app.logger.debug("cart view empty from service but session has items -> using session fallback")
                items, total_cents = _session_view()
        except Exception:
            # On any exception, fallback to session cart
            current_app.logger.exception("cart.view failed, using session fallback")
            items, total_cents = _session_view()
    else:
        # No service: use session cart
        items, total_cents = _session_view()

    # cart_total passed to template in euros (cents/100)
    return render_template("cart.html", items=items, cart_total=(total_cents or 0)/100)

@cart_bp.route("/cart/remove/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    """
    Remove a product from the cart.
    - Try cart service remove(product_id, 0) if available.
    - Otherwise remove from session cart.
    """
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
            flash("Produit supprimé du panier.", "info")
    else:
        cart = session.get("cart", {})
        cart.pop(product_id, None)
        session["cart"] = cart
        flash("Produit supprimé du panier.", "info")
    return redirect(url_for("cart.view_cart"))

@cart_bp.route("/cart/update", methods=["POST"])
@cart_bp.route("/cart/update/<product_id>", methods=["POST"])
def update_cart(product_id=None):
    """
    Update cart quantities.
    - If product_id is provided: handle single-item update.
      * Try cart_svc.set_quantity if available.
      * Otherwise compute delta and call cart_svc.add/remove if supported.
      * Falls back to session update on any error.
    - If no product_id: handle full-cart update using form keys quantities[<product_id>].
      * If cart service is absent, update session directly.
      * If cart service present, compute deltas and delegate to add/remove on service.
    """
    services = current_app.extensions.get("services", {})
    cart_svc = services.get("cart")

    # helper that sets a specific pid quantity in session cart
    def _session_set(pid, qty):
        cart = session.get("cart", {})
        if qty <= 0:
            cart.pop(pid, None)
        else:
            cart[pid] = qty
        session["cart"] = cart

    # single-item update (template posts with product_id)
    if product_id:
        try:
            qty = int(request.form.get("qty", request.form.get("quantity", 0)))
        except Exception:
            qty = 0

        if cart_svc and hasattr(cart_svc, "view"):
            # Prefer direct set if service supports it
            if hasattr(cart_svc, "set_quantity"):
                try:
                    cart_svc.set_quantity(product_id, qty)
                    flash("Panier mis à jour.", "success")
                    return redirect(url_for("cart.view_cart"))
                except Exception:
                    current_app.logger.exception("cart.set_quantity failed")
            # Otherwise compute current quantity then call add/remove to reach target qty
            try:
                items, _ = cart_svc.view()
                current = 0
                for it in items:
                    # Support both dict and object shapes returned by service
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
                    # If service cannot handle, update session directly
                    _session_set(product_id, qty)
                flash("Panier mis à jour.", "success")
                return redirect(url_for("cart.view_cart"))
            except Exception:
                current_app.logger.exception("cart.update single-item failed, using session fallback")
                _session_set(product_id, qty)
                flash("Panier mis à jour (session fallback).", "warning")
                return redirect(url_for("cart.view_cart"))
        else:
            # No service: update session cart
            _session_set(product_id, qty)
            flash("Panier mis à jour.", "success")
            return redirect(url_for("cart.view_cart"))

    # full-cart update: parse form keys quantities[<pid>]
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

    # If service present: compute current quantities and apply deltas using add/remove on service
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

    # Apply deltas based on submitted form
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