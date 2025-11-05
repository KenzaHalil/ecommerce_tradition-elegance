from flask import Blueprint, session, redirect, url_for, render_template
from app.services_init import products

wishlist_bp = Blueprint("wishlist", __name__)

def get_wishlist():
    return session.setdefault("wishlist", [])

@wishlist_bp.route("/wishlist/add/<product_id>", methods=["POST"])
def add_to_wishlist(product_id):
    wishlist = get_wishlist()
    if product_id not in wishlist:
        wishlist.append(product_id)
    session["wishlist"] = wishlist
    return redirect(url_for("catalogue.catalogue"))

@wishlist_bp.route("/wishlist")
def view_wishlist():
    wishlist = get_wishlist()
    items = [products.get(pid) for pid in wishlist if products.get(pid)]
    return render_template("wishlist.html", items=items)