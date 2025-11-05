import os
from flask import Flask, redirect, url_for
from .models import db
from .services_init import init_services

def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    if config:
        app.config.update(config)

    # Initialiser SQLAlchemy correctement
    try:
        db.init_app(app)
    except Exception:
        app.logger.debug("db.init_app failed or db already initialized")

    # Initialiser les services (auth, products, cart, ...)
    try:
        init_services(app)
    except Exception:
        app.logger.debug("init_services failed")

    # Enregistrer les blueprints (catalogue, auth, admin, cart, order, etc.)
    # Ajuste les import paths si nécessaire
    try:
        from .routes.catalogue_routes import catalogue_bp
        app.register_blueprint(catalogue_bp)
    except Exception:
        app.logger.debug("catalogue blueprint missing")

    try:
        from .routes.auth_routes import auth_bp
        app.register_blueprint(auth_bp)
    except Exception:
        app.logger.debug("auth blueprint missing")

    try:
        from .routes.admin_routes import admin_bp
        app.register_blueprint(admin_bp)
    except Exception:
        app.logger.debug("admin blueprint missing")

    try:
        from .routes.cart_routes import cart_bp
        app.register_blueprint(cart_bp)
    except Exception:
        app.logger.debug("cart blueprint missing")

    try:
        # order_routes définit bp = Blueprint('order_bp', ...)
        from .routes.order_routes import bp as order_bp
        app.register_blueprint(order_bp)
    except Exception:
        app.logger.debug("order blueprint missing")

    # Route racine -> redirige vers le catalogue (évite 404 sur '/')
    @app.route("/")
    def index():
        return redirect(url_for("catalogue.catalogue"))

    return app
