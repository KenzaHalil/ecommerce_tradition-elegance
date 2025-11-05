from typing import Optional, List, Dict
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session as flask_session, current_app
from app import db
from app.models import User, Product, Order, OrderItem, Cart, CartItem, Payment, Invoice, InvoiceLine
import uuid
import datetime

# Repositories
class UserRepository:
    def add(self, user: User):
        db.session.add(user)
        db.session.flush()
        return user

    def get(self, user_id: str) -> Optional[User]:
        return User.query.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

class ProductRepository:
    def get(self, product_id: str) -> Optional[Product]:
        return Product.query.get(product_id)

    def list_active(self) -> List[Product]:
        return Product.query.all()

    def reserve_stock(self, product_id: str, qty: int):
        p = self.get(product_id)
        if not p or p.stock_qty < qty:
            raise ValueError("Stock insuffisant.")
        p.stock_qty -= qty
        db.session.add(p)

    def release_stock(self, product_id: str, qty: int):
        p = self.get(product_id)
        if p:
            p.stock_qty += qty
            db.session.add(p)

class OrderRepository:
    def add(self, order: Order):
        db.session.add(order)
        db.session.flush()
        return order

    def get(self, order_id: str) -> Optional[Order]:
        return Order.query.get(order_id)

    def list_by_user(self, user_id: str):
        return Order.query.filter_by(user_id=user_id).all()

    def update(self, order: Order):
        db.session.add(order)
        db.session.flush()
        return order

# Services
class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def register(self, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
        if self.users.get_by_email(email):
            raise ValueError("Email déjà utilisé.")
        user = User(email=email, first_name=first_name, last_name=last_name)
        if hasattr(user, "set_password"):
            user.set_password(password)
        else:
            user.password_hash = generate_password_hash(password)
        self.users.add(user)
        db.session.commit()
        return user

    def login(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user:
            raise ValueError("Identifiants invalides.")
        if hasattr(user, "check_password"):
            ok = user.check_password(password)
        else:
            ok = check_password_hash(getattr(user, "password_hash", ""), password)
        if not ok:
            raise ValueError("Identifiants invalides.")
        return user

class CatalogService:
    def __init__(self, products: ProductRepository):
        self.products = products

    def list_products(self):
        return self.products.list_active()

class CartService:
    def __init__(self, products: ProductRepository):
        self.products = products

    def _get_session_cart(self) -> Dict[str,int]:
        return flask_session.setdefault("cart", {})

    def add(self, product_id: str, qty: int = 1):
        p = self.products.get(product_id)
        if not p:
            raise ValueError("Produit introuvable.")
        cart = self._get_session_cart()
        cart[product_id] = cart.get(product_id, 0) + qty
        flask_session["cart"] = cart

    def remove(self, product_id: str, qty: int = 1):
        cart = self._get_session_cart()
        if product_id not in cart:
            return
        if qty <= 0:
            cart.pop(product_id, None)
        else:
            cart[product_id] = max(0, cart[product_id] - qty)
            if cart[product_id] == 0:
                cart.pop(product_id, None)
        flask_session["cart"] = cart

    def view(self):
        cart = self._get_session_cart()
        items = []
        total = 0
        for pid, qty in cart.items():
            p = self.products.get(pid)
            if not p:
                continue
            subtotal = p.price_cents * qty
            items.append({"product": p, "quantity": qty, "subtotal_cents": subtotal, "subtotal_eur": subtotal/100})
            total += subtotal
        return items, total

    def clear(self):
        flask_session["cart"] = {}

class PaymentGateway:
    def charge_card(self, card_number: str, exp_month: int, exp_year: int, cvc: str, amount_cents: int, idempotency_key: str) -> dict:
        ok = not str(card_number).endswith("0000")
        return {"success": ok, "transaction_id": str(uuid.uuid4()) if ok else None, "failure_reason": None if ok else "CARD_DECLINED"}

    def refund(self, transaction_id, amount_cents):
        return {"success": True, "refund_id": str(uuid.uuid4())}

class OrderService:
    def __init__(self, orders: OrderRepository, products: ProductRepository, billing=None):
        self.orders = orders
        self.products = products
        self.billing = billing

    def checkout(self, user_id: str, session_cart: Dict[str,int]) -> Order:
        if not session_cart:
            raise ValueError("Panier vide.")
        # created_at must be a datetime object for DateTime columns
        order = Order(user_id=user_id, items=[], status="CREE", created_at=datetime.datetime.utcnow())
        db.session.add(order)
        db.session.flush()
        total = 0
        for pid, qty in session_cart.items():
            p = self.products.get(pid)
            if not p or p.stock_qty < qty:
                db.session.rollback()
                raise ValueError(f"Produit indisponible: {pid}")
            p.stock_qty -= qty
            db.session.add(p)
            oi = OrderItem(order_id=order.id, product_id=p.id, quantity=qty, price_cents=p.price_cents)
            db.session.add(oi)
            total += p.price_cents * qty
        # assign total before commit
        if hasattr(order, "total_cents"):
            order.total_cents = total
        db.session.commit()
        return order

    def pay_by_card(self, order_id, card_number, exp_month, exp_year, cvc):
        order = Order.query.get(order_id)
        if not order:
            raise ValueError("Commande introuvable.")
        gw = current_app.extensions["services"]["gateway"]
        res = gw.charge_card(card_number, exp_month, exp_year, cvc, order.total_cents, idempotency_key=str(order.id))
        pay = Payment(order_id=order.id, user_id=order.user_id, amount_cents=order.total_cents, provider="CB", provider_ref=res.get("transaction_id"), succeeded=1 if res["success"] else 0)
        db.session.add(pay)
        if not res["success"]:
            db.session.commit()
            raise ValueError("Paiement refusé.")
        # crée facture minimale
        inv = Invoice(order_id=order.id, user_id=order.user_id, total_cents=order.total_cents)
        db.session.add(inv); db.session.flush()
        for oi in OrderItem.query.filter_by(order_id=order.id).all():
            line = InvoiceLine(invoice_id=inv.id, product_id=oi.product_id, name=oi.product.name if oi.product else None, unit_price_cents=oi.price_cents, quantity=oi.quantity, line_total_cents=oi.price_cents*oi.quantity)
            db.session.add(line)
        order.payment_id = pay.id
        order.invoice_id = inv.id
        order.status = "PAYEE"
        db.session.commit()
        return pay

def create_services():
    user_repo = UserRepository()
    prod_repo = ProductRepository()
    order_repo = OrderRepository()
    auth_svc = AuthService(user_repo)
    catalog_svc = CatalogService(prod_repo)
    cart_svc = CartService(prod_repo)
    order_svc = OrderService(order_repo, prod_repo)
    return {
        "user_repo": user_repo,
        "prod_repo": prod_repo,
        "order_repo": order_repo,
        "auth": auth_svc,
        "catalog": catalog_svc,
        "cart": cart_svc,
        "order": order_svc,
        "gateway": PaymentGateway()
    }