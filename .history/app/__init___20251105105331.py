import os
from flask import Flask, Blueprint
from .models import db  # utilise l'instance unique définie dans models.py
from pathlib import Path
import pkgutil, importlib
from .services_init import init_services

def create_app(config: dict | None = None):
    app = Flask(__name__, instance_relative_config=False)
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

    # SECRET_KEY nécessaire pour utiliser flask.session
    # en production : exporte SECRET_KEY dans les variables d'environnement
    # prefer explicit config + set secret on the app object so session is available immediately
    secret = os.environ.get("SECRET_KEY", "elegance-dev-key")
    app.config["SECRET_KEY"] = secret
    app.secret_key = secret

    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{PROJECT_ROOT / 'elegance.db'}")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    if config:
        app.config.update(config)

    # initialise l'extension avec l'app
    db.init_app(app)

    # ensure services container exists
    app.extensions.setdefault("services", {})

    # try to populate services from app.services:
    try:
        svc_mod = importlib.import_module("app.services")
        # prefer an init_services(app) if provided
        if hasattr(svc_mod, "init_services"):
            svc_mod.init_services(app)
        # otherwise call create_services() and store returned dict
        elif hasattr(svc_mod, "create_services"):
            created = svc_mod.create_services()
            if isinstance(created, dict):
                app.extensions["services"].update(created)
    except Exception:
        # ne pas planter l'app si services manquent — routes gèreront l'erreur plus tard
        pass

    # auto-enregistrer blueprints présents dans app.routes.*
    try:
        import app.routes as routes_pkg
        for finder, name, ispkg in pkgutil.iter_modules(routes_pkg.__path__):
            mod = importlib.import_module(f"app.routes." + name)
            for obj in vars(mod).values():
                if isinstance(obj, Blueprint):
                    app.register_blueprint(obj)
    except Exception:
        pass

    init_services(app)

    return app
