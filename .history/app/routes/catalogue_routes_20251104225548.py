from flask import Blueprint, render_template
from app.models import Product

catalogue_bp = Blueprint("catalogue", __name__)

@catalogue_bp.route("/catalogue")
def catalogue():
    all_products = Product.query.all()
    categories = {
        "Kabyle": {"title": "Robes Kabyles", "desc": "Découvrez nos robes kabyles traditionnelles, brodées à la main."},
        "Abaya": {"title": "Abayas Orientales", "desc": "Abayas élégantes, fluides et modernes pour toutes les occasions."},
        "Caftan": {"title": "Caftans Marocains", "desc": "Caftans marocains raffinés, ornés de broderies et de perles."},
        "Karakou": {"title": "Karakous Algériens", "desc": "Karakous en velours, broderies dorées, symbole d’élégance algérienne."}
    }
    grouped = {cat: [] for cat in categories}
    for p in all_products:
        if p.category in grouped:
            grouped[p.category].append(p)
    return render_template("catalogue.html", categories=categories, grouped=grouped)

@catalogue_bp.route("/product/<product_id>")
def product_detail(product_id):
    product = products.get(product_id)
    if not product:
        return redirect(url_for("catalogue.catalogue"))
    return render_template("product_detail.html", product=product)