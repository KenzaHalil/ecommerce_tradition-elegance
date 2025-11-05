from app.domain import (
    UserRepository, ProductRepository, CartRepository, OrderRepository,
    InvoiceRepository, PaymentRepository, ThreadRepository,
    SessionManager, AuthService, CatalogService, CartService,
    BillingService, DeliveryService, PaymentGateway, OrderService, CustomerService, Product
)
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from werkzeug.security import check_password_hash

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
order_svc = OrderService(orders, products, carts, payments, invoices, billing, delivery_svc, gateway, users)
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
    description="Noir profond, coupe ample.",
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

def init_services(app):
    """Initialise app.extensions['services'] — appeler dans create_app(app)"""
    services = {
        "auth": auth,
        "products": products,
        "cart": cart_svc,
        # ajouter ici d'autres services si nécessaire
    }
    app.extensions = getattr(app, "extensions", {})
    app.extensions["services"] = services
    return services
