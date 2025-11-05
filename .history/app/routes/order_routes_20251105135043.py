from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app
from uuid import uuid4
from datetime import datetime
from app.models import db, Cart, CartItem, Order, OrderItem, Payment, Delivery, Product

order_bp = Blueprint("order", __name__)

def gen_tracking_number():
    return "TRK" + uuid4().hex[:12].upper()

@order_bp.route("/order/create", methods=['POST'])
def create_order():
    # récupération user (adapter selon ton auth)
    user_id = session.get('user_id') or request.form.get('user_id')
    if not user_id:
        flash("Utilisateur non identifié.", "danger")
        return redirect(url_for('catalogue.catalogue'))

    # récupérer panier
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        flash("Panier introuvable.", "warning")
        return redirect(url_for('catalogue.catalogue'))

    items = CartItem.query.filter_by(cart_user_id=cart.user_id).all()
    if not items:
        flash("Panier vide.", "warning")
        return redirect(url_for('catalogue.catalogue'))

    # calcul total
    total_cents = 0
    for it in items:
        prod = Product.query.get(it.product_id)
        if not prod: continue
        total_cents += (prod.price_cents or 0) * (it.quantity or 0)

    # créer order
    order = Order(user_id=user_id, status='CREATED', total_cents=total_cents, created_at=datetime.utcnow())
    db.session.add(order)
    db.session.flush()  # obtenir order.id

    # snapshot items -> order_item
    for it in items:
        prod = Product.query.get(it.product_id)
        if not prod: continue
        oi = OrderItem(order_id=order.id, product_id=it.product_id, quantity=it.quantity, price_cents=prod.price_cents)
        db.session.add(oi)

    # ici : appel vers ton provider / validation du paiement
    # pour l'instant on enregistre un paiement simulé succeeded=True
    payment = Payment(
        order_id=order.id,
        user_id=user_id,
        amount_cents=total_cents,
        provider=request.form.get('provider', 'manual'),
        provider_ref=request.form.get('provider_ref', ''),
        succeeded=True,
        created_at=datetime.utcnow()
    )
    db.session.add(payment)

    # marquer order comme payé et set paid_at
    order.status = 'PAYEE'
    order.paid_at = datetime.utcnow()

    # créer delivery + tracking
    tracking = gen_tracking_number()
    delivery = Delivery(
        order_id=order.id,
        carrier=request.form.get('carrier', 'Transporteur'),
        tracking_number=tracking,
        address=request.form.get('address', None),
        status='pending',
        updated_at=datetime.utcnow().isoformat()
    )
    db.session.add(delivery)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Erreur lors de la création de la commande.", "danger")
        return redirect(url_for('catalogue.catalogue'))

    # vider panier (silently)
    try:
        CartItem.query.filter_by(cart_user_id=cart.user_id).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()

    # REDIRECTION vers page de confirmation (affiche le tracking)
    return redirect(url_for('order_bp.confirm', order_id=order.id))

@order_bp.route('/order/confirm/<int:order_id>', methods=['GET'])
def confirm(order_id):
    order = Order.query.get_or_404(order_id)
    tn = None
    if order.delivery:
        tn = order.delivery.tracking_number
    return render_template('order/confirmation.html', order=order, tracking_number=tn)

@order_bp.route("/order/my-orders")
def my_orders():
    uid = session.get("user_id")
    current_app.logger.debug("my-orders route session user_id: %r", uid)
    if uid is None:
        flash("Connectez-vous pour voir vos commandes.", "warning")
        return redirect(url_for("auth.login"))

    services = current_app.extensions.get("services", {})
    order_svc = services.get("order")
    if not order_svc:
        current_app.logger.error("order service missing in services")
        flash("Service de commande indisponible.", "danger")
        return redirect(url_for "catalogue.catalogue")

    # try lookup with multiple representations
    candidates = []
    try:
        candidates.append(uid)
        if isinstance(uid, str) and uid.isdigit():
            candidates.append(int(uid))
        if isinstance(uid, int):
            candidates.append(str(uid))
    except Exception:
        pass

    orders = []
    for cand in candidates:
        try:
            current_app.logger.debug("Trying get_user_orders(%r)", cand)
            orders = order_svc.get_user_orders(cand) or []
            current_app.logger.debug("Found %d orders for %r", len(orders), cand)
            if orders:
                break
        except Exception:
            current_app.logger.exception("order_svc.get_user_orders failed for %r", cand)
            orders = []

    # ensure items normalized for templates (subtotal_cents etc.)
    def _normalize_orders(raw_orders):
        out = []
        for o in raw_orders or []:
            its = []
            for it in o.get("items", []) if isinstance(o, dict) else getattr(o, "items", []):
                if isinstance(it, dict):
                    pid = it.get("product_id") or it.get("id")
                    qty = int(it.get("quantity", 1))
                    price = int(it.get("price_cents", 0))
                    subtotal = int(it.get("subtotal_cents", price * qty))
                else:
                    pid = getattr(it, "product_id", None) or getattr(it, "id", None)
                    qty = int(getattr(it, "quantity", 1))
                    price = int(getattr(it, "price_cents", 0) or 0)
                    subtotal = price * qty
                its.append({"product_id": pid, "quantity": qty, "price_cents": price, "subtotal_cents": subtotal})
            # récupère tracking_number s'il existe (dict ou objet)
            tracking = None
            if isinstance(o, dict):
                tracking = o.get("tracking_number") or (o.get("delivery") and o["delivery"].get("tracking_number")) if o.get("delivery") else o.get("tracking_number")
            else:
                tracking = getattr(o, "tracking_number", None) or (getattr(getattr(o, "delivery", None), "tracking_number", None))
            out.append({
                "id": o.get("id") if isinstance(o, dict) else getattr(o, "id", None),
                "status": o.get("status") if isinstance(o, dict) else getattr(o, "status", None),
                "total_cents": int(o.get("total_cents", 0) if isinstance(o, dict) else getattr(o, "total_cents", 0)),
                "items": its,
                "created_at": o.get("created_at") if isinstance(o, dict) else getattr(o, "created_at", None),
                "tracking_number": tracking
            })
        return out

    orders = _normalize_orders(orders)
    # use the existing template under app/templates/account/
    return render_template("account/orders.html", orders=orders)