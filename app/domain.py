from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional
import uuid
import time
import hashlib


# =========================
# ======= DOMAIN =========
# =========================

class OrderStatus(Enum):
    CREE = auto()
    VALIDEE = auto()
    PAYEE = auto()
    EXPEDIEE = auto()
    LIVREE = auto()
    ANNULEE = auto()
    REMBOURSEE = auto()


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    address: str
    city: str = ""
    postal_code: str = ""
    phone: str = ""
    is_admin: bool = False

    def update_profile(self, **fields):
        for k, v in fields.items():
            if hasattr(self, k) and k not in {"id", "email", "is_admin", "password_hash"}:
                setattr(self, k, v)


@dataclass
class Product:
    id: str
    name: str
    description: str
    price_cents: int
    stock_qty: int = 0
    category: str = ""


@dataclass
class CartItem:
    product_id: str
    quantity: int


@dataclass
class Cart:
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)  # key: product_id

    def add(self, product: Product, qty: int = 1):
        if qty <= 0:
            raise ValueError("Quantité invalide.")
        if not product.active:
            raise ValueError("Produit inactif.")
        if product.stock_qty < qty:
            raise ValueError("Stock insuffisant.")
        if product.id in self.items:
            self.items[product.id].quantity += qty
        else:
            self.items[product.id] = CartItem(product_id=product.id, quantity=qty)

    def remove(self, product_id: str, qty: int = 1):
        if product_id not in self.items:
            return
        if qty <= 0:
            # remove completely
            del self.items[product_id]
            return
        self.items[product_id].quantity -= qty
        if self.items[product_id].quantity <= 0:
            del self.items[product_id]

    def clear(self):
        self.items.clear()

    def total_cents(self, product_repo: "ProductRepository") -> int:
        total = 0
        for it in self.items.values():
            p = product_repo.get(it.product_id)
            if p is None or not p.active:
                continue
            total += p.price_cents * it.quantity
        return total


@dataclass
class InvoiceLine:
    product_id: str
    name: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int


@dataclass
class Invoice:
    id: str
    order_id: str
    user_id: str
    lines: List[InvoiceLine]
    total_cents: int
    issued_at: float  # epoch timestamp


@dataclass
class Payment:
    id: str
    order_id: str
    user_id: str
    amount_cents: int
    provider: str  # ex: "CB"
    provider_ref: Optional[str]
    succeeded: bool
    created_at: float


@dataclass
class Delivery:
    id: str
    order_id: str
    carrier: str
    tracking_number: Optional[str]
    address: str
    status: str  # ex: "PREPAREE", "EN_COURS", "LIVREE"


@dataclass
class MessageThread:
    id: str
    user_id: str
    order_id: Optional[str]
    subject: str
    messages: List["Message"] = field(default_factory=list)
    closed: bool = False


@dataclass
class Message:
    id: str
    thread_id: str
    author_user_id: Optional[str]  # None = agent support
    body: str
    created_at: float


@dataclass
class OrderItem:
    product_id: str
    name: str
    unit_price_cents: int
    quantity: int


@dataclass
class Order:
    id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    created_at: float
    validated_at: Optional[float] = None
    paid_at: Optional[float] = None
    shipped_at: Optional[float] = None
    delivered_at: Optional[float] = None
    cancelled_at: Optional[float] = None
    refunded_at: Optional[float] = None
    delivery: Optional[Delivery] = None
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None

    def total_cents(self) -> int:
        return sum(i.unit_price_cents * i.quantity for i in self.items)


# =========================
# ===== REPOSITORIES ======
# =========================

class UserRepository:
    def __init__(self):
        self._by_id: Dict[str, User] = {}
        self._by_email: Dict[str, User] = {}

    def add(self, user: User):
        self._by_id[user.id] = user
        self._by_email[user.email.lower()] = user

    def get(self, user_id: str) -> Optional[User]:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self._by_email.get(email.lower())


class ProductRepository:
    def __init__(self):
        self._products = []
        self._by_id = {}  # Ajout de l'attribut manquant

    def add(self, product):
        self._products.append(product)
        self._by_id[product.id] = product  # Mise à jour du dictionnaire

    def list_all(self):
        return self._products

    def get(self, product_id: str):
        return self._by_id.get(product_id)

    def list_active(self) -> List[Product]:
        return [p for p in self._by_id.values() if p.active]

    def reserve_stock(self, product_id: str, qty: int):
        p = self.get(product_id)
        if not p or p.stock_qty < qty:
            raise ValueError("Stock insuffisant.")
        p.stock_qty -= qty

    def release_stock(self, product_id: str, qty: int):
        p = self.get(product_id)
        if p:
            p.stock_qty += qty


class CartRepository:
    def __init__(self):
        self._by_user: Dict[str, Cart] = {}

    def get_or_create(self, user_id: str) -> Cart:
        if user_id not in self._by_user:
            self._by_user[user_id] = Cart(user_id=user_id)
        return self._by_user[user_id]

    def clear(self, user_id: str):
        self.get_or_create(user_id).clear()


class OrderRepository:
    def __init__(self):
        self._by_id: Dict[str, Order] = {}
        self._by_user: Dict[str, List[str]] = {}

    def add(self, order: Order):
        self._by_id[order.id] = order
        self._by_user.setdefault(order.user_id, []).append(order.id)

    def get(self, order_id: str) -> Optional[Order]:
        return self._by_id.get(order_id)

    def list_by_user(self, user_id: str) -> List[Order]:
        return [self._by_id[oid] for oid in self._by_user.get(user_id, [])]

    def update(self, order: Order):
        self._by_id[order.id] = order


class InvoiceRepository:
    def __init__(self):
        self._by_id: Dict[str, Invoice] = {}

    def add(self, invoice: Invoice):
        self._by_id[invoice.id] = invoice

    def get(self, invoice_id: str) -> Optional[Invoice]:
        return self._by_id.get(invoice_id)


class PaymentRepository:
    def __init__(self):
        self._by_id: Dict[str, Payment] = {}

    def add(self, payment: Payment):
        self._by_id[payment.id] = payment

    def get(self, payment_id: str) -> Optional[Payment]:
        return self._by_id.get(payment_id)


class ThreadRepository:
    def __init__(self):
        self._by_id: Dict[str, MessageThread] = {}

    def add(self, thread: MessageThread):
        self._by_id[thread.id] = thread

    def get(self, thread_id: str) -> Optional[MessageThread]:
        return self._by_id.get(thread_id)

    def list_by_user(self, user_id: str) -> List[MessageThread]:
        return [t for t in self._by_id.values() if t.user_id == user_id]


# =========================
# ====== UTIL / AUTH =====
# =========================

class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        # Simple but deterministic: use sha256; in prod utiliser bcrypt/argon2 + salt
        h = hashlib.sha256()
        h.update(password.encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def verify(password: str, stored_hash: str) -> bool:
        return PasswordHasher.hash(password) == stored_hash


class SessionManager:
    """Gestion simple de sessions en mémoire."""
    def __init__(self):
        self._sessions: Dict[str, str] = {}  # token -> user_id

    def create_session(self, user_id: str) -> str:
        token = str(uuid.uuid4())
        self._sessions[token] = user_id
        return token

    def destroy_session(self, token: str):
        self._sessions.pop(token, None)

    def get_user_id(self, token: str) -> Optional[str]:
        return self._sessions.get(token)


class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionManager):
        self.users = users
        self.sessions = sessions

    def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        address: str,
        city: str,
        postal_code: str,
        phone: str = "",
        is_admin: bool = False
    ) -> User:
        if self.users.get_by_email(email):
            raise ValueError("Email déjà utilisé.")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=PasswordHasher.hash(password),
            first_name=first_name,
            last_name=last_name,
            address=address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            is_admin=is_admin
        )
        self.users.add(user)
        return user

    def login(self, email: str, password: str) -> str:
        user = self.users.get_by_email(email)
        if not user or not PasswordHasher.verify(password, user.password_hash):
            raise ValueError("Identifiants invalides.")
        return self.sessions.create_session(user.id)

    def logout(self, token: str):
        self.sessions.destroy_session(token)


# =========================
# ====== SERVICES =========
# =========================

class CatalogService:
    def __init__(self, products: ProductRepository):
        self.products = products

    def list_products(self) -> List[Product]:
        return self.products.list_active()


class CartService:
    def __init__(self, carts: CartRepository, products: ProductRepository):
        self.carts = carts
        self.products = products

    def add_to_cart(self, user_id: str, product_id: str, qty: int = 1):
        product = self.products.get(product_id)
        if not product:
            raise ValueError("Produit introuvable.")
        self.carts.get_or_create(user_id).add(product, qty)

    def remove_from_cart(self, user_id: str, product_id: str, qty: int = 1):
        self.carts.get_or_create(user_id).remove(product_id, qty)

    def view_cart(self, user_id: str) -> Cart:
        return self.carts.get_or_create(user_id)

    def cart_total(self, user_id: str) -> int:
        return self.carts.get_or_create(user_id).total_cents(self.products)


class PaymentGateway:
    """Simulation d'un prestataire CB (à remplacer par Stripe/Adyen/etc.)."""
    def charge_card(self, card_number: str, exp_month: int, exp_year: int, cvc: str, amount_cents: int, idempotency_key: str) -> Dict:
        # MOCK: succès si la carte ne finit pas par '0000'
        ok = not card_number.endswith("0000")
        return {
            "success": ok,
            "transaction_id": str(uuid.uuid4()) if ok else None,
            "failure_reason": None if ok else "CARTE_REFUSEE"
        }

    def refund(self, transaction_id: str, amount_cents: int) -> Dict:
        # toujours success dans le mock
        return {
            "success": True,
            "refund_id": str(uuid.uuid4())
        }


class BillingService:
    def __init__(self, invoices: InvoiceRepository):
        self.invoices = invoices

    def issue_invoice(self, order: Order) -> Invoice:
        lines = [
            InvoiceLine(
                product_id=i.product_id,
                name=i.name,
                unit_price_cents=i.unit_price_cents,
                quantity=i.quantity,
                line_total_cents=i.unit_price_cents * i.quantity
            )
            for i in order.items
        ]
        inv = Invoice(
            id=str(uuid.uuid4()),
            order_id=order.id,
            user_id=order.user_id,
            lines=lines,
            total_cents=sum(l.line_total_cents for l in lines),
            issued_at=time.time()
        )
        self.invoices.add(inv)
        return inv


class DeliveryService:
    def prepare_delivery(self, order: Order, address: str, carrier: str = "POSTE") -> Delivery:
        delivery = Delivery(
            id=str(uuid.uuid4()),
            order_id=order.id,
            carrier=carrier,
            tracking_number=None,
            address=address,
            status="PREPAREE"
        )
        return delivery

    def ship(self, delivery: Delivery) -> Delivery:
        delivery.status = "EN_COURS"
        delivery.tracking_number = delivery.tracking_number or f"TRK-{uuid.uuid4().hex[:10].upper()}"
        return delivery

    def mark_delivered(self, delivery: Delivery) -> Delivery:
        delivery.status = "LIVREE"
        return delivery


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        carts: CartRepository,
        payments: PaymentRepository,
        invoices: InvoiceRepository,
        billing: BillingService,
        delivery_svc: DeliveryService,
        gateway: PaymentGateway,
        users: UserRepository
    ):
        self.orders = orders
        self.products = products
        self.carts = carts
        self.payments = payments
        self.invoices = invoices
        self.billing = billing
        self.delivery_svc = delivery_svc
        self.gateway = gateway
        self.users = users

    # ----- core flows -----

    def checkout(self, user_id: str) -> Order:
        cart = self.carts.get_or_create(user_id)
        if not cart.items:
            raise ValueError("Panier vide.")
        # Réserver le stock
        order_items: List[OrderItem] = []
        for it in cart.items.values():
            p = self.products.get(it.product_id)
            if not p or not p.active:
                raise ValueError("Produit indisponible.")
            if p.stock_qty < it.quantity:
                raise ValueError(f"Stock insuffisant pour {p.name}.")
            self.products.reserve_stock(p.id, it.quantity)
            order_items.append(OrderItem(
                product_id=p.id,
                name=p.name,
                unit_price_cents=p.price_cents,
                quantity=it.quantity
            ))
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            items=order_items,
            status=OrderStatus.CREE,
            created_at=time.time()
        )
        self.orders.add(order)
        # vider le panier
        self.carts.clear(user_id)
        return order

    def pay_by_card(self, order_id: str, card_number: str, exp_month: int, exp_year: int, cvc: str) -> Payment:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Commande introuvable.")
        if order.status not in {OrderStatus.CREE, OrderStatus.VALIDEE}:
            raise ValueError("Statut de commande incompatible avec le paiement.")
        amount = order.total_cents()
        res = self.gateway.charge_card(
            card_number, exp_month, exp_year, cvc, amount, idempotency_key=order.id
        )
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order.id,
            user_id=order.user_id,
            amount_cents=amount,
            provider="CB",
            provider_ref=res.get("transaction_id"),
            succeeded=res["success"],
            created_at=time.time()
        )
        self.payments.add(payment)
        if not payment.succeeded:
            raise ValueError("Paiement refusé.")
        order.payment_id = payment.id
        order.status = OrderStatus.PAYEE
        order.paid_at = time.time()
        # Facture
        inv = self.billing.issue_invoice(order)
        order.invoice_id = inv.id
        self.orders.update(order)
        return payment

    def view_orders(self, user_id: str) -> List[Order]:
        return self.orders.list_by_user(user_id)

    def request_cancellation(self, user_id: str, order_id: str) -> Order:
        order = self.orders.get(order_id)
        if not order or order.user_id != user_id:
            raise ValueError("Commande introuvable.")
        if order.status in {OrderStatus.EXPEDIEE, OrderStatus.LIVREE}:
            raise ValueError("Trop tard pour annuler : commande expédiée.")
        order.status = OrderStatus.ANNULEE
        order.cancelled_at = time.time()
        # restituer le stock
        for it in order.items:
            self.products.release_stock(it.product_id, it.quantity)
        self.orders.update(order)
        return order

    # ----- backoffice -----

    def backoffice_validate_order(self, admin_user_id: str, order_id: str) -> Order:
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.CREE:
            raise ValueError("Commande introuvable ou mauvais statut.")
        order.status = OrderStatus.VALIDEE
        order.validated_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_ship_order(self, admin_user_id: str, order_id: str) -> Order:
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.PAYEE:
            raise ValueError("La commande doit être payée pour être expédiée.")
        user = self.users.get(order.user_id)
        if not user:
            raise ValueError("Utilisateur introuvable.")
        delivery = self.delivery_svc.prepare_delivery(order, address=user.address)
        delivery = self.delivery_svc.ship(delivery)
        order.delivery = delivery
        order.status = OrderStatus.EXPEDIEE
        order.shipped_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_mark_delivered(self, admin_user_id: str, order_id: str) -> Order:
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.EXPEDIEE or not order.delivery:
            raise ValueError("Commande non expédiée.")
        self.delivery_svc.mark_delivered(order.delivery)
        order.status = OrderStatus.LIVREE
        order.delivered_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_refund(self, admin_user_id: str, order_id: str, amount_cents: Optional[int] = None) -> Order:
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status not in {OrderStatus.PAYEE, OrderStatus.ANNULEE}:
            raise ValueError("Remboursement non autorisé au statut actuel.")
        amount = amount_cents or order.total_cents()
        payment = self.payments.get(order.payment_id) if order.payment_id else None
        if not payment or not payment.provider_ref:
            raise ValueError("Aucun paiement initial.")
        self.gateway.refund(payment.provider_ref, amount)
        order.status = OrderStatus.REMBOURSEE
        order.refunded_at = time.time()
        # restituer le stock si besoin
        for it in order.items:
            self.products.release_stock(it.product_id, it.quantity)
        self.orders.update(order)
        return order


class CustomerService:
    """Service client: fils de discussion & messages côté UI + réponses agents."""
    def __init__(self, threads: ThreadRepository, users: UserRepository):
        self.threads = threads
        self.users = users

    def open_thread(self, user_id: str, subject: str, order_id: Optional[str] = None) -> MessageThread:
        th = MessageThread(id=str(uuid.uuid4()), user_id=user_id, order_id=order_id, subject=subject)
        self.threads.add(th)
        return th

    def post_message(self, thread_id: str, author_user_id: Optional[str], body: str) -> Message:
        th = self.threads.get(thread_id)
        if not th or th.closed:
            raise ValueError("Fil introuvable ou fermé.")
        if author_user_id is not None and not self.users.get(author_user_id):
            raise ValueError("Auteur inconnu.")
        msg = Message(id=str(uuid.uuid4()), thread_id=thread_id, author_user_id=author_user_id, body=body, created_at=time.time())
        th.messages.append(msg)
        return msg

    def close_thread(self, thread_id: str, admin_user_id: str):
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        th = self.threads.get(thread_id)
        if not th:
            raise ValueError("Fil introuvable.")
        th.closed = True
        return th


# =========================
# ======= BOOTSTRAP =======
# =========================

if __name__ == "__main__":
    # Repos & services
    users = UserRepository()
    products = ProductRepository()
    carts = CartRepository()
    orders = OrderRepository()
    invoices = InvoiceRepository()
    payments = PaymentRepository()
    threads = ThreadRepository()
    sessions = SessionManager()

    auth = AuthService(users, sessions)
    catalog = CatalogService(products)
    cart_svc = CartService(carts, products)
    billing = BillingService(invoices)
    delivery_svc = DeliveryService()
    gateway = PaymentGateway()
    order_svc = OrderService(orders, products, carts, payments, invoices, billing, delivery_svc, gateway, users)
    cs = CustomerService(threads, users)

    # create sample products
    p1 = Product(id=str(uuid.uuid4()), name="T-Shirt Logo", description="Coton bio", price_cents=1999, stock_qty=100)
    p2 = Product(id=str(uuid.uuid4()), name="Sweat Capuche", description="Molleton", price_cents=4999, stock_qty=50)
    products.add(p1); products.add(p2)

    # create users
    admin = auth.register("admin@shop.test", "admin", "Admin", "Root", "1 Rue du BO", is_admin=True)
    client = auth.register("client@shop.test", "secret", "Alice", "Martin", "12 Rue des Fleurs", "Paris", "75000", "0123456789")

    token = auth.login("client@shop.test", "secret")
    user_id = sessions.get_user_id(token)

    # Affichage catalogue
    print("Produits:", [f"{p.name} {p.price_cents/100:.2f}€" for p in catalog.list_products()])

    # add to cart
    cart_svc.add_to_cart(user_id, p1.id, 2)
    cart_svc.add_to_cart(user_id, p2.id, 1)
    print("Total panier €:", cart_svc.cart_total(user_id)/100)

    # checkout
    order = order_svc.checkout(user_id)
    print("Commande créée:", order.id, "Total €:", order.total_cents()/100)

    # validate
    order = order_svc.backoffice_validate_order(admin.id, order.id)
    print("Commande validée:", order.status)

    # pay
    payment = order_svc.pay_by_card(order.id, "4242424242424242", 12, 2030, "123")
    print("Paiement OK:", payment.provider_ref)

    # ship & deliver
    order = order_svc.backoffice_ship_order(admin.id, order.id)
    print("Expédiée, tracking:", order.delivery.tracking_number)
    order = order_svc.backoffice_mark_delivered(admin.id, order.id)
    print("Statut:", order.status)

    # support thread
    th = cs.open_thread(user_id, "Taille trop petite", order_id=order.id)
    cs.post_message(th.id, user_id, "Bonjour, je souhaite échanger le T-Shirt.")
    cs.post_message(th.id, None, "Bonjour, nous pouvons proposer un échange. Merci de renvoyer l'article.")
    cs.close_thread(th.id, admin.id)
    print("Fil messages:", len(th.messages), "Fermé:", th.closed)

    auth.logout(token)

