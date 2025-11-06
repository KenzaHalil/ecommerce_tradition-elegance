from datetime import datetime
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy

# Création d'une instance unique de SQLAlchemy
# Elle servira à interagir avec la base de données
db = SQLAlchemy()

# --------------------------
# 🔹 TABLE UTILISATEUR (User)
# --------------------------
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)  # Identifiant unique
    email = db.Column(db.String(120), unique=True, nullable=False)  # Email unique
    password_hash = db.Column(db.String(128), nullable=False)  # Mot de passe haché
    first_name = db.Column(db.String(50))  # Prénom
    last_name = db.Column(db.String(50))   # Nom
    profile_image = db.Column(db.Text, default=None)  # Photo de profil (optionnelle)
    is_admin = db.Column(db.Boolean, default=False)  # Statut administrateur
    address = db.Column(db.Text)  # Adresse postale de l'utilisateur

    # Relations avec les autres tables
    carts = db.relationship("Cart", back_populates="user", uselist=True)
    orders = db.relationship("Order", back_populates="user", uselist=True)
    payments = db.relationship("Payment", back_populates="user", uselist=True)
    threads = db.relationship("MessageThread", back_populates="user", uselist=True)


# ----------------------------
# 🔹 TABLE PRODUIT (Product)
# ----------------------------
class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.String(50), primary_key=True)  # ID du produit (chaîne unique)
    name = db.Column(db.String(100), nullable=False)  # Nom du produit
    description = db.Column(db.Text)  # Description
    price_cents = db.Column(db.Integer, nullable=False)  # Prix en centimes (évite les erreurs flottantes)
    stock_qty = db.Column(db.Integer)  # Quantité en stock
    category = db.Column(db.String(50))  # Catégorie (ex : Kabyle, Caftan…)
    active = db.Column(db.Boolean, default=True)  # Produit actif ou non

    # Relations avec d'autres tables
    order_items = db.relationship("OrderItem", back_populates="product", lazy="select")
    cart_items = db.relationship("CartItem", back_populates="product", lazy="select")


# ----------------------------
# 🔹 TABLE PANIER (Cart)
# ----------------------------
class Cart(db.Model):
    __tablename__ = "cart"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)  # Chaque panier appartient à un utilisateur
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))  # Date de création

    # Relations
    user = db.relationship("User", back_populates="carts")
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


# ----------------------------------
# 🔹 TABLE ÉLÉMENTS DU PANIER (CartItem)
# ----------------------------------
class CartItem(db.Model):
    __tablename__ = "cart_item"
    id = db.Column(db.Integer, primary_key=True)
    cart_user_id = db.Column(db.Integer, db.ForeignKey("cart.user_id"), nullable=False)  # Lien vers le panier
    product_id = db.Column(db.String(50), db.ForeignKey("product.id"), nullable=False)   # Lien vers le produit
    quantity = db.Column(db.Integer, nullable=False, default=1)  # Quantité du produit
    size = db.Column(db.String(10))  # Taille sélectionnée (ex : S, M, L…)

    # Relations
    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product", back_populates="cart_items")


# ------------------------------
# 🔹 TABLE COMMANDE (Order)
# ------------------------------
class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Lien vers l'utilisateur
    status = db.Column(db.String(20))  # Statut (PENDING, PAID, SHIPPED, DELIVERED…)
    total_cents = db.Column(db.Integer)  # Montant total en centimes
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))  # Date de création
    payment_id = db.Column(db.Integer)  # ID du paiement (facultatif)
    invoice_id = db.Column(db.Integer)  # ID de la facture (facultatif)

    # Suivi des différentes étapes
    validated_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)

    # Relations
    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    delivery = db.relationship("Delivery", back_populates="order", uselist=False)


# ----------------------------------
# 🔹 TABLE ÉLÉMENTS DE COMMANDE (OrderItem)
# ----------------------------------
class OrderItem(db.Model):
    __tablename__ = "order_item"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.String(50), db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_cents = db.Column(db.Integer, nullable=False)

    # Relations
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")


# ----------------------------
# 🔹 TABLE FACTURE (Invoice)
# ----------------------------
class Invoice(db.Model):
    __tablename__ = "invoice"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer)  # Lien vers la commande
    user_id = db.Column(db.Integer)   # Lien vers l'utilisateur
    total_cents = db.Column(db.Integer)
    issued_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))  # Date d’émission
    lines = db.relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


# ---------------------------------
# 🔹 TABLE LIGNES DE FACTURE (InvoiceLine)
# ---------------------------------
class InvoiceLine(db.Model):
    __tablename__ = "invoice_line"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    product_id = db.Column(db.String(50))
    name = db.Column(db.String(255))
    unit_price_cents = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    line_total_cents = db.Column(db.Integer)

    # Relation avec la facture
    invoice = db.relationship("Invoice", back_populates="lines")


# ----------------------------
# 🔹 TABLE PAIEMENT (Payment)
# ----------------------------
class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))  # Lien vers la commande
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))    # Lien vers l’utilisateur
    amount_cents = db.Column(db.Integer)  # Montant payé
    provider = db.Column(db.String(50))   # Fournisseur (ex : Stripe, PayPal…)
    provider_ref = db.Column(db.String(128))  # Référence de transaction
    succeeded = db.Column(db.Boolean, server_default=text("0"))  # Paiement réussi ?
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))  # Date du paiement

    # Relations
    order = db.relationship("Order", back_populates="payments")
    user = db.relationship("User", back_populates="payments")


# ----------------------------
# 🔹 TABLE LIVRAISON (Delivery)
# ----------------------------
class Delivery(db.Model):
    __tablename__ = "delivery"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))  # Lien vers la commande
    carrier = db.Column(db.String(50))  # Transporteur (ex : Colissimo, DHL…)
    tracking_number = db.Column(db.String(128), unique=True)  # Numéro de suivi unique
    address = db.Column(db.Text)  # Adresse de livraison
    status = db.Column(db.String(30))  # Statut (en préparation, en transit, livré…)
    tracking_url = db.Column(db.Text)  # Lien de suivi
    shipped_at = db.Column(db.Text)  # Date d’expédition
    delivered_at = db.Column(db.Text)  # Date de livraison
    updated_at = db.Column(db.Text)  # Dernière mise à jour du suivi

    order = db.relationship("Order", back_populates="delivery")


# ----------------------------------------
# 🔹 TABLE FIL DE DISCUSSION (MessageThread)
# ----------------------------------------
class MessageThread(db.Model):
    __tablename__ = "message_thread"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Lien vers l’utilisateur
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))  # Lien vers la commande
    subject = db.Column(db.String(255))  # Sujet du message (ex : "Problème de livraison")
    closed = db.Column(db.Boolean, server_default=text("0"))  # Discussion clôturée ?

    user = db.relationship("User", back_populates="threads")
    messages = db.relationship("Message", back_populates="thread", cascade="all, delete-orphan")


# ----------------------------
# 🔹 TABLE MESSAGE (Message)
# ----------------------------
class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("message_thread.id"), nullable=False)  # Lien vers la discussion
    author_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # Auteur du message
    body = db.Column(db.Text)  # Contenu du message
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))  # Date d’envoi

    # Relations
    thread = db.relationship("MessageThread", back_populates="messages")
    author = db.relationship("User")  # Lien vers l'auteur
