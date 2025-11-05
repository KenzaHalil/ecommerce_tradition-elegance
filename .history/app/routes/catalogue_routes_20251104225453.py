"""
Routes du catalogue produit.

- Ce module doit fournir la route /catalogue (ou /) qui rend la liste des produits.
- Le modèle Product est utilisé ; selon l'implémentation Product peut être un ORM (SQLAlchemy)
  ou un simple wrapper autour du repo. Adapter les tests/mocks en conséquence.
- Vérifier que les templates référencés existent (catalogue.html, product_detail.html).
"""
from flask import Blueprint, render_template
from app.models import Product

catalogue_bp = Blueprint("catalogue", __name__)

@catalogue_bp.route("/catalogue")
def catalogue():
    """
    Affiche la page catalogue.
    - Récupère les produits via Product.query.all() ou API équivalente.
    - Le template doit gérer la structure des objets produits (id, name, price_cents, stock_qty, category).
    """
    # adaptation possible : Product.query.all() ou Product.list_all()
    try:
        products = Product.query.all()
    except Exception:
        # fallback : si Product expose une autre API.
        try:
            products = Product.list_all()
        except Exception:
            products = []
    return render_template("catalogue.html", products=products)

@catalogue_bp.route("/product/<product_id>")
def product_detail(product_id):
    product = products.get(product_id)
    if not product:
        return redirect(url_for("catalogue.catalogue"))
    return render_template("product_detail.html", product=product)