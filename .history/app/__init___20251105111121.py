import os
from flask import Flask
from .models import db
from .services_init import init_services

def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # config minimale
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    if config:
        app.config.update(config)

    # init DB if present
    try:
        db.init_app(app)
    except Exception:
        pass

    # initialiser services (auth, products, cart...)
    init_services(app)

    # enregistrer blueprints (ajoute d'autres blueprints si nécessaire)
    try:
        from .routes.auth_routes import auth_bp
        from .routes.catalogue_routes import catalogue_bp
        from .routes.admin_routes import admin_bp
        from .routes.cart_routes import cart_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(catalogue_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(cart_bp)
    except Exception:
        # en dev, ignorer si un blueprint manque
        app.logger.debug("Some blueprints not found/failed to register")

    return app
