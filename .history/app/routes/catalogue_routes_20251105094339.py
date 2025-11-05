from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Product

catalogue_bp = Blueprint("catalogue", __name__)

@catalogue_bp.route("/catalogue")
def catalogue():
    # lecture de la query string 'q' pour la recherche
    q = (request.args.get("q") or "").strip()

    all_products = []
    # try simple SQLAlchemy optimized filter first, fallback to in‑python filtering
    try:
        # si SQLAlchemy disponible, on peut faire un filtre plus efficace
        if q:
            from sqlalchemy import or_
            products_list = Product.query.filter(
                or_(
                    Product.name.ilike(f"%{q}%"),
                    Product.description.ilike(f"%{q}%")
                )
            ).all()
        else:
            products_list = Product.query.all()
    except Exception:
        # fallback: tenter d'obtenir tout puis filtrer en Python (supporte dicts/objets)
        try:
            all_products = Product.query.all()
        except Exception:
            try:
                all_products = Product.list_all()
            except Exception:
                all_products = []

        if q:
            ql = q.lower()
            def matches(p):
                name = getattr(p, "name", None) or (p.get("name") if hasattr(p, "get") else "") or ""
                desc = getattr(p, "description", None) or (p.get("description") if hasattr(p, "get") else "") or ""
                return ql in name.lower() or ql in desc.lower()
            products_list = [p for p in all_products if matches(p)]
        else:
            products_list = all_products

    # catégories et regroupement (affiche uniquement les produits filtrés si q fourni)
    categories = {
        "Kabyle": {"title": "Robes Kabyles", "desc": "Découvrez nos robes kabyles traditionnelles, brodées à la main."},
        "Abaya": {"title": "Abayas Orientales", "desc": "Abayas élégantes, fluides et modernes pour toutes les occasions."},
        "Caftan": {"title": "Caftans Marocains", "desc": "Caftans marocains raffinés, ornés de broderies et de perles."},
        "Karakou": {"title": "Karakous Algériens", "desc": "Karakous en velours, broderies dorées, symbole d’élégance algérienne."}
    }
    grouped = {cat: [] for cat in categories}
    for p in products_list:
        cat = getattr(p, "category", None) or (p.get("category") if hasattr(p, "get") else None)
        if cat in grouped:
            grouped[cat].append(p)

    return render_template(
        "catalogue.html",
        categories=categories,
        grouped=grouped,
        search_query=q,
        search_mode=bool(q),
        results_count=len(products_list)
    )

@catalogue_bp.route("/product/<product_id>")
def product_detail(product_id):
    product = products.get(product_id)
    if not product:
        return redirect(url_for("catalogue.catalogue"))
    return render_template("product_detail.html", product=product)