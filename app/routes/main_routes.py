from flask import Blueprint, render_template
from app.services_init import catalog

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    products = catalog.list_products()
    return render_template("index.html", products=products)
