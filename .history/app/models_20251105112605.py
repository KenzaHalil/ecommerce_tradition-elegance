from datetime import datetime
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy

# create single SQLAlchemy instance without binding to an app here
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    profile_image = db.Column(db.Text, default=None)
    is_admin = db.Column(db.Boolean, default=False)
    address = db.Column(db.Text)

    carts = db.relationship("Cart", back_populates="user", uselist=True)
    orders = db.relationship("Order", back_populates="user", uselist=True)
    payments = db.relationship("Payment", back_populates="user", uselist=True)
    threads = db.relationship("MessageThread", back_populates="user", uselist=True)


class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_cents = db.Column(db.Integer, nullable=False)
    stock_qty = db.Column(db.Integer)
    category = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)

    order_items = db.relationship("OrderItem", back_populates="product", lazy="select")
    cart_items = db.relationship("CartItem", back_populates="product", lazy="select")


class Cart(db.Model):
    __tablename__ = "cart"
    # DB uses user_id as primary key for cart
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = db.relationship("User", back_populates="carts")
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(db.Model):
    __tablename__ = "cart_item"
    id = db.Column(db.Integer, primary_key=True)
    cart_user_id = db.Column(db.Integer, db.ForeignKey("cart.user_id"), nullable=False)
    product_id = db.Column(db.String(50), db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    size = db.Column(db.String(10))

    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product", back_populates="cart_items")


class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20))
    total_cents = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))
    payment_id = db.Column(db.Integer)   # optional FK depending on app logic
    invoice_id = db.Column(db.Integer)
    validated_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    delivery = db.relationship("Delivery", back_populates="order", uselist=False)


class OrderItem(db.Model):
    __tablename__ = "order_item"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.String(50), db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_cents = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")


class Invoice(db.Model):
    __tablename__ = "invoice"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    total_cents = db.Column(db.Integer)
    issued_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))
    lines = db.relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(db.Model):
    __tablename__ = "invoice_line"
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    product_id = db.Column(db.String(50))
    name = db.Column(db.String(255))
    unit_price_cents = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    line_total_cents = db.Column(db.Integer)

    invoice = db.relationship("Invoice", back_populates="lines")


class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    amount_cents = db.Column(db.Integer)
    provider = db.Column(db.String(50))
    provider_ref = db.Column(db.String(128))
    succeeded = db.Column(db.Boolean, server_default=text("0"))
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))

    order = db.relationship("Order", back_populates="payments")
    user = db.relationship("User", back_populates="payments")


class Delivery(db.Model):
    __tablename__ = "delivery"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    carrier = db.Column(db.String(50))
    tracking_number = db.Column(db.String(128), unique=True)
    address = db.Column(db.Text)
    status = db.Column(db.String(30))
    tracking_url = db.Column(db.Text)
    shipped_at = db.Column(db.Text)
    delivered_at = db.Column(db.Text)
    updated_at = db.Column(db.Text)

    order = db.relationship("Order", back_populates="delivery")


class MessageThread(db.Model):
    __tablename__ = "message_thread"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    subject = db.Column(db.String(255))
    closed = db.Column(db.Boolean, server_default=text("0"))

    user = db.relationship("User", back_populates="threads")
    messages = db.relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("message_thread.id"), nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=text("CURRENT_TIMESTAMP"))

    thread = db.relationship("MessageThread", back_populates="messages")
    author = db.relationship("User")