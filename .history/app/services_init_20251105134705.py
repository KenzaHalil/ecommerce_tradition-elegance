from app.domain import (
    UserRepository, ProductRepository, CartRepository, OrderRepository,
    InvoiceRepository, PaymentRepository, ThreadRepository,
    SessionManager, AuthService, CatalogService, CartService,
    BillingService, DeliveryService, PaymentGateway, OrderService, CustomerService, Product
)
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from pathlib import Path
import sqlite3, os, uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "elegance.db"

def _connect():
    return sqlite3.connect(str(DB_PATH))

class AuthService:
    """Service minimal pour récupérer utilisateur et vérifier mot de passe."""
    def __init__(self, *args, **kwargs):
        """
        Compatibilité : accepte des arguments optionnels (users, sessions, ...)
        pour éviter TypeError si le module fait AuthService(users, sessions).
        Stocke les références si fournies.
        """
        self._users = kwargs.get("users", args[0] if len(args) > 0 else None)
        self._sessions = kwargs.get("sessions", args[1] if len(args) > 1 else None)
        # initialisation minimale (adapter si la classe attend d'autres attributs)
        # ... existing code ...

    def get_by_email(self, email):
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT id,email,password_hash,first_name,last_name,is_admin FROM user WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "first_name": row[3],
            "last_name": row[4],
            "is_admin": bool(row[5])
        }

    def verify_password(self, user, password):
        if not user or not user.get("password_hash"):
            return False
        return check_password_hash(user["password_hash"], password)

    # Ajout : méthode login attendue par d'autres parties du code
    def login(self, email, password):
        """
        Vérifie email/password et renvoie l'utilisateur (dict) si OK, sinon None.
        Si un SessionManager a été fourni, crée/retourne aussi une session via celui-ci.
        """
        user = None
        # si on a un repository users passé, utiliser son API
        if self._users:
            try:
                user = self._users.get_by_email(email)
            except Exception:
                user = None
        # fallback DB lookup local si repository non fourni
        if not user:
            user = self.get_by_email(email)
        if not user:
            return None
        if not self.verify_password(user, password):
            return None
        # si on a un session manager, créer une session (optionnel)
        if self._sessions and hasattr(self._sessions, "create"):
            try:
                sess = self._sessions.create(user["id"])
                # retourne la paire (user, session) si nécessaire
                return {"user": user, "session": sess}
            except Exception:
                # ne bloquer pas l'auth si la création de session échoue
                return {"user": user}
        return {"user": user}

    def register(self, email: str, password: str, first_name: str = "", last_name: str = "", is_admin: bool = False):
        """
        Crée un nouvel utilisateur dans la table `user`.
        Lève RuntimeError si l'email existe déjà ou ValueError si données invalides.
        Retourne un dict utilisateur minimal en cas de succès.
        """
        email = (email or "").strip()
        password = (password or "").strip()
        if not email or not password:
            raise ValueError("email et mot de passe requis")

        db_path = Path(__file__).resolve().parents[1] / "elegance.db"
        if not db_path.exists():
            raise RuntimeError("Base de données introuvable")

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # vérifier existence email
        cur.execute("SELECT id FROM user WHERE email = ?", (email,))
        if cur.fetchone():
            conn.close()
            raise RuntimeError("Un compte avec cet email existe déjà.")

        pw_hash = generate_password_hash(password)
        # INSERT sans created_at (évite l'erreur si la colonne n'existe pas)
        cur.execute(
            "INSERT INTO user (email, password_hash, first_name, last_name, is_admin) VALUES (?, ?, ?, ?, ?)",
            (email, pw_hash, first_name or None, last_name or None, 1 if is_admin else 0)
        )
        conn.commit()
        uid = cur.lastrowid
        conn.close()
        return {"id": uid, "email": email, "first_name": first_name, "last_name": last_name, "is_admin": bool(is_admin)}

class ProductService:
    """Service minimal pour lister/supprimer produits utilisé par l'admin."""
    def list_all(self):
        conn = _connect()
        cur = conn.cursor()
        cur.execute("SELECT id,name,description,price_cents,stock_qty,category,active FROM product ORDER BY id")
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append(SimpleNamespace(
                id=r[0], name=r[1], description=r[2], price_cents=r[3],
                stock_qty=r[4], category=r[5], active=r[6]
            ))
        return out

    def delete(self, product_id):
        conn = _connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM product WHERE id = ?", (product_id,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if not affected:
            raise RuntimeError("Produit introuvable")
        return affected

class CartAdapter:
    """
    Adaptateur pour fournir l'API minimale attendue par les routes :
    - view() -> (items, total_cents)
    - add(product_id, qty)
    - remove(product_id, qty)
    Il délègue aux méthodes disponibles du service réel (cart_svc) avec des fallbacks.
    """
    def __init__(self, svc):
        self._svc = svc

    def add(self, product_id, qty=1):
        if hasattr(self._svc, "add"):
            return self._svc.add(product_id, qty)
        if hasattr(self._svc, "add_item"):
            return self._svc.add_item(product_id, qty)
        if hasattr(self._svc, "add_to_cart"):
            return self._svc.add_to_cart(product_id, qty)
        raise RuntimeError("Cart service has no compatible add method")

    def remove(self, product_id, qty=0):
        # qty==0 -> remove line
        if hasattr(self._svc, "remove"):
            return self._svc.remove(product_id, qty)
        if hasattr(self._svc, "remove_item"):
            return self._svc.remove_item(product_id, qty)
        if hasattr(self._svc, "set_quantity"):
            return self._svc.set_quantity(product_id, 0)
        if hasattr(self._svc, "delete"):
            return self._svc.delete(product_id)
        raise RuntimeError("Cart service has no compatible remove method")

    def view(self):
        # try direct view
        if hasattr(self._svc, "view"):
            return self._svc.view()
        # common alternative: get_cart() returning dict or object
        if hasattr(self._svc, "get_cart"):
            cart = self._svc.get_cart()
            if isinstance(cart, dict):
                items = cart.get("items", [])
                total = cart.get("total_cents", 0)
            else:
                items = getattr(cart, "items", []) or []
                total = getattr(cart, "total_cents", 0) or getattr(cart, "total", 0)
            return items, total
        # list_items fallback
        if hasattr(self._svc, "list_items"):
            items = self._svc.list_items()
            total = 0
            for it in items:
                # try different shapes
                qty = getattr(it, "quantity", None) or (it.get("quantity") if isinstance(it, dict) else 1)
                price = getattr(it, "price_cents", None) or (it.get("price_cents") if isinstance(it, dict) else 0)
                total += (price or 0) * (qty or 1)
            return items, total
        # default empty cart
        return [], 0

class DevOrderService:
    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        conn = _connect()
        cur = conn.cursor()
        # ensure order table exists (keeps existing schema)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS "order" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status VARCHAR(20),
                total_cents INTEGER,
                created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
                payment_id INTEGER,
                invoice_id INTEGER,
                validated_at DATETIME,
                paid_at DATETIME,
                shipped_at DATETIME,
                delivered_at DATETIME,
                cancelled_at DATETIME,
                refunded_at DATETIME
            )
        """)
        # ensure order_item table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS order_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                product_id TEXT,
                quantity INTEGER,
                price_cents INTEGER
            )
        """)
        # add tracking_number column if missing
        cur.execute('PRAGMA table_info("order")')
        cols = [r[1] for r in cur.fetchall()]
        if "tracking_number" not in cols:
            cur.execute('ALTER TABLE "order" ADD COLUMN tracking_number TEXT')
        conn.commit()
        conn.close()

    def create_order(self, user_id, items, total_cents, status="PENDING"):
        import datetime
        uid = int(user_id) if user_id is not None else None
        now = datetime.datetime.utcnow().isoformat()
        conn = _connect()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO "order" (user_id, status, total_cents, created_at) VALUES (?, ?, ?, ?)',
            (uid, status, int(total_cents or 0), now)
        )
        order_id = cur.lastrowid
        for it in items or []:
            if isinstance(it, dict):
                pid = str(it.get("product_id") or it.get("id") or "")
                qty = int(it.get("quantity", 1))
                price = int(it.get("price_cents", 0))
            else:
                pid = str(getattr(it, "product_id", "") or getattr(it, "id", ""))
                qty = int(getattr(it, "quantity", 1))
                price = int(getattr(it, "price_cents", 0) or 0)
            cur.execute(
                "INSERT INTO order_item (order_id, product_id, quantity, price_cents) VALUES (?, ?, ?, ?)",
                (order_id, pid, qty, price)
            )
        conn.commit()
        conn.close()
        return {"id": order_id, "user_id": uid, "items": items, "total_cents": int(total_cents or 0), "status": status, "created_at": now}

    def get_user_orders(self, user_id):
        uid = int(user_id) if isinstance(user_id, (str, int)) and str(user_id).isdigit() else user_id
        conn = _connect()
        cur = conn.cursor()
        cur.execute('SELECT id, total_cents, status, created_at, tracking_number FROM "order" WHERE user_id = ? ORDER BY created_at DESC', (uid,))
        rows = cur.fetchall()
        out = []
        for r in rows:
            oid, total_cents, status, created_at, tracking = r
            cur.execute("SELECT product_id, quantity, price_cents FROM order_item WHERE order_id = ?", (oid,))
            its = []
            for pit, qty, price in cur.fetchall():
                its.append({
                    "product_id": pit,
                    "quantity": qty,
                    "price_cents": price,
                    "subtotal_cents": int(price or 0) * int(qty or 0)
                })
            out.append({
                "id": oid,
                "user_id": uid,
                "items": its,
                "total_cents": int(total_cents or 0),
                "status": status,
                "created_at": created_at,
                "tracking_number": tracking
            })
        conn.close()
        return out

    def get_order(self, order_id):
        conn = _connect()
        cur = conn.cursor()
        cur.execute('SELECT id, user_id, total_cents, status, created_at, tracking_number FROM "order" WHERE id = ?', (order_id,))
        r = cur.fetchone()
        if not r:
            conn.close()
            return None
        oid, uid, total_cents, status, created_at, tracking = r
        cur.execute("SELECT product_id, quantity, price_cents FROM order_item WHERE order_id = ?", (oid,))
        its = []
        for pit, qty, price in cur.fetchall():
            its.append({
                "product_id": pit,
                "quantity": qty,
                "price_cents": price,
                "subtotal_cents": int(price or 0) * int(qty or 0)
            })
        conn.close()
        return {"id": oid, "user_id": uid, "items": its, "total_cents": int(total_cents or 0), "status": status, "created_at": created_at, "tracking_number": tracking}

    def set_status(self, order_id, status):
        conn = _connect()
        cur = conn.cursor()
        cur.execute('UPDATE "order" SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
        conn.close()
        return True

    def set_tracking(self, order_id, tracking_number):
        conn = _connect()
        cur = conn.cursor()
        cur.execute('UPDATE "order" SET tracking_number = ? WHERE id = ?', (tracking_number, order_id))
        conn.commit()
        conn.close()
        return True
# Création des repositories et services
users = UserRepository()
products = ProductRepository()
carts = CartRepository()
orders = OrderRepository()
invoices = InvoiceRepository()
payments = PaymentRepository()
threads = ThreadRepository()
sessions = SessionManager()

# créer auth en passant users/sessions (conserver cette instance)
auth = AuthService(users, sessions)
catalog = CatalogService(products)
cart_svc = CartService(carts, products)
billing = BillingService(invoices)
delivery_svc = DeliveryService()
gateway = PaymentGateway()
# tentative de création du service de commande, fallback sur DevOrderService en cas d'échec
try:
    # si OrderService demande des dépendances (implémentation domaine), tenter la création
    order_svc = OrderService(orders, products, carts, payments, invoices, billing, delivery_svc, gateway, users)
except Exception:
    # fallback : utiliser le service en mémoire
    order_svc = DevOrderService()
cs = CustomerService(threads, users)

# Ajout des produits traditionnels
products.add(Product(
    id="robe_kabyle",
    name="Robe Kabyle Prestige",
    description="Robe traditionnelle kabyle brodée à la main, motifs berbères colorés.",
    price_cents=15900,
    stock_qty=10,
    category="Kabyle"
))
products.add(Product(
    id="abaya_orientale",
    name="Abaya Orientale Chic",
    description="Abaya fluide et élégante, tissu léger, finitions dorées.",
    price_cents=9900,
    stock_qty=15,
    category="Orientale"
))
products.add(Product(
    id="caftan_marocain",
    name="Caftan Marocain Élégance",
    description="Caftan marocain moderne, ornements dorés et coupe raffinée.",
    price_cents=18900,
    stock_qty=8,
    category="Marocain"
))
products.add(Product(
    id="ferguani",
    name="Ferguani Tradition",
    description="Robe ferguani, tissu artisanal, broderies fines.",
    price_cents=12900,
    stock_qty=12,
    category="Algérien"
))
products.add(Product(
    id="tlemcani",
    name="Tlemcani Authentique",
    description="Robe tlemcani, coupe traditionnelle, motifs floraux.",
    price_cents=14900,
    stock_qty=7,
    category="Algérien"
))

# Ajout des produits modernes
products.add(Product(
    id="robe_kabyle_1",
    name="Robe Kabyle Prestige",
    description="Broderie berbère, tissu premium.",
    price_cents=15900,
    stock_qty=5,
    category="Kabyle"
))
products.add(Product(
    id="robe_kabyle_2",
    name="Robe Kabyle Élégance",
    description="Motifs floraux, coupe moderne.",
    price_cents=14900,
    stock_qty=3,
    category="Kabyle"
))
products.add(Product(
    id="robe_kabyle_3",
    name="Robe Kabyle Tradition",
    description="Couleurs vives, ceinture tissée.",
    price_cents=13900,
    stock_qty=4,
    category="Kabyle"
))
products.add(Product(
    id="caftan_1",
    name="Caftan Marocain Or",
    description="Ornements dorés, coupe royale.",
    price_cents=18900,
    stock_qty=2,
    category="Caftan"
))
products.add(Product(
    id="caftan_2",
    name="Caftan Bleu Nuit",
    description="Velours bleu, broderie argent.",
    price_cents=17900,
    stock_qty=3,
    category="Caftan"
))
products.add(Product(
    id="caftan_3",
    name="Caftan Classique",
    description="Coupe traditionnelle, tissu léger.",
    price_cents=16900,
    stock_qty=5,
    category="Caftan"
))
products.add(Product(
    id="abaya_1",
    name="Abaya Orientale Chic",
    description="Tissu fluide, finitions dorées.",
    price_cents=9900,
    stock_qty=6,
    category="Abaya"
))
products.add(Product(
    id="abaya_2",
    name="Abaya Noire Élégante",
    description="Noir profond, coupe moderne.",
    price_cents=10900,
    stock_qty=4,
    category="Abaya"
))
products.add(Product(
    id="abaya_3",
    name="Abaya Blanche Pureté",
    description="Blanc cassé, détails subtils.",
    price_cents=11900,
    stock_qty=3,
    category="Abaya"
))
products.add(Product(
    id="karakou_1",
    name="Karakou Vert Olive",
    description="Velours vert, broderie dorée.",
    price_cents=19900,
    stock_qty=2,
    category="Karakou"
))
products.add(Product(
    id="karakou_2",
    name="Karakou Bordeaux Élégance",
    description="Bordeaux profond, coupe raffinée.",
    price_cents=20900,
    stock_qty=3,
    category="Karakou"
))
products.add(Product(
    id="karakou_3",
    name="Karakou Tradition",
    description="Motifs classiques, tissu premium.",
    price_cents=18900,
    stock_qty=2,
    category="Karakou"
))

# ATTENTION : ne pas écraser 'auth' ci‑dessous — supprimer la réassignation
# auth = AuthService()   <-- supprimer cette ligne si présente

def _wrap_order_service(raw):
    """
    Retourne un adaptateur exposant create_order(user_id, items, total_cents),
    get_user_orders(user_id), get_order(order_id) et set_status(order_id, status).
    Si raw fournit déjà ces méthodes on les délègue, sinon on tente des noms alternatifs,
    sinon on fournit un fallback en mémoire (DevOrderService).
    """
    if not raw:
        return DevOrderService()

    # helper to find an attribute among several possible names
    def _find_attr(obj, names):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

    # if raw already implements full API, return it
    has_create = hasattr(raw, "create_order")
    has_get_user = hasattr(raw, "get_user_orders")
    has_get_one = hasattr(raw, "get_order")
    has_set_status = hasattr(raw, "set_status")

    if has_create and has_get_user and has_get_one:
        return raw

    # try to discover equivalent methods
    create_fn = _find_attr(raw, ("create_order", "create", "place_order", "placeOrder", "createOrder", "make_order", "new_order"))
    get_user_fn = _find_attr(raw, ("get_user_orders", "list_user_orders", "list_orders_for_user", "orders_for_user", "user_orders"))
    get_one_fn = _find_attr(raw, ("get_order", "find_order", "order_by_id", "find_by_id"))
    set_status_fn = _find_attr(raw, ("set_status", "update_status", "mark_paid", "setOrderStatus"))

    # if we found nothing for create, fallback to DevOrderService
    if not create_fn:
        return DevOrderService()

    class OrderAdapter:
        def __init__(self, raw, create_fn, get_user_fn, get_one_fn, set_status_fn):
            self._raw = raw
            self._create = create_fn
            self._get_user = get_user_fn
            self._get_one = get_one_fn
            self._set_status = set_status_fn
            # expose underlying storage if present (helpful for debug)
            if hasattr(raw, "_orders"):
                self._orders = getattr(raw, "_orders")

        def create_order(self, user_id, items, total_cents, status="PENDING"):
            # try to call create with common signatures
            try:
                return self._create(user_id, items, total_cents)
            except TypeError:
                # maybe signature is (items, user_id, total) or different — try permutations
                try:
                    return self._create(items, user_id, total_cents)
                except Exception:
                    return self._create(user_id, items)  # best-effort

        def get_user_orders(self, user_id):
            if self._get_user:
                return self._get_user(user_id)
            # try list all and filter if raw exposes list/get_all
            if hasattr(self._raw, "list_orders"):
                allo = self._raw.list_orders()
                return [o for o in allo if str(o.get("user_id")) == str(user_id)]
            return []

        def get_order(self, order_id):
            if self._get_one:
                return self._get_one(order_id)
            if hasattr(self._raw, "find_order"):
                return self._raw.find_order(order_id)
            return None

        def set_status(self, order_id, status):
            if self._set_status:
                return self._set_status(order_id, status)
            # best-effort mutate in-memory list if present
            if hasattr(self, "_orders"):
                for o in self._orders:
                    if o.get("id") == order_id:
                        o["status"] = status
                        return o
            raise RuntimeError("set_status not supported")

    return OrderAdapter(raw, create_fn, get_user_fn, get_one_fn, set_status_fn)

# wrap the raw order service instance to guarantee the expected API
try:
    wrapped_order_svc = _wrap_order_service(order_svc)
except Exception:
    wrapped_order_svc = DevOrderService()

def init_services(app):
    services = {
        "auth": auth,
        "products": products,
        "cart": CartAdapter(cart_svc),
        "order": wrapped_order_svc,
        "payment": gateway,
    }
    app.extensions = getattr(app, "extensions", {})
    app.extensions["services"] = services
    return services
