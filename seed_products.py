from app import create_app, db
from app.models import Product

PRODUCTS = [
    # Robes Kabyles
    {"id":"robe_kabyle_1","name":"Robe Kabyle Prestige","description":"Broderie berbère","price_cents":15900,"stock_qty":5,"category":"Kabyle"},
    {"id":"robe_kabyle_2","name":"Robe Kabyle Élégance","description":"Motifs floraux","price_cents":14900,"stock_qty":3,"category":"Kabyle"},
    {"id":"robe_kabyle_3","name":"Robe Kabyle Tradition","description":"Couleurs vives","price_cents":13900,"stock_qty":4,"category":"Kabyle"},
    # Caftans
    {"id":"caftan_1","name":"Caftan Marocain Or","description":"Ornements dorés","price_cents":18900,"stock_qty":2,"category":"Caftan"},
    {"id":"caftan_2","name":"Caftan Bleu Nuit","description":"Velours bleu","price_cents":17900,"stock_qty":3,"category":"Caftan"},
    {"id":"caftan_3","name":"Caftan Classique","description":"Coupe traditionnelle","price_cents":16900,"stock_qty":5,"category":"Caftan"},
    # Abayas
    {"id":"abaya_1","name":"Abaya Orientale Chic","description":"Tissu fluide","price_cents":9900,"stock_qty":6,"category":"Abaya"},
    {"id":"abaya_2","name":"Abaya Noire Élégante","description":"Noir profond","price_cents":10900,"stock_qty":4,"category":"Abaya"},
    {"id":"abaya_3","name":"Abaya Blanche Pureté","description":"Blanc cassé","price_cents":11900,"stock_qty":3,"category":"Abaya"},
    # Karakous
    {"id":"karakou_1","name":"Karakou Vert Olive","description":"Velours vert","price_cents":19900,"stock_qty":2,"category":"Karakou"},
    {"id":"karakou_2","name":"Karakou Bordeaux Élégance","description":"Bordeaux profond","price_cents":20900,"stock_qty":3,"category":"Karakou"},
    {"id":"karakou_3","name":"Karakou Tradition","description":"Motifs classiques","price_cents":18900,"stock_qty":2,"category":"Karakou"},
]

def main():
    app = create_app()
    with app.app_context():
        added = 0
        skipped = 0
        for p in PRODUCTS:
            if Product.query.get(p["id"]):
                skipped += 1
                continue
            prod = Product(
                id=p["id"],
                name=p["name"],
                description=p["description"],
                price_cents=p["price_cents"],
                stock_qty=p["stock_qty"],
                category=p["category"]
            )
            db.session.add(prod)
            added += 1
        try:
            if added:
                db.session.commit()
            print(f"Ajoutés: {added}, ignorés (déjà présents): {skipped}")
        except Exception as e:
            db.session.rollback()
            print("Erreur lors du commit:", e)

if __name__ == "__main__":
    main()