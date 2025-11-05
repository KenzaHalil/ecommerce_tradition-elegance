from app import create_app
app = create_app()
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess.pop("cart", None); sess.pop("user_id", None); sess.pop("_flashes", None)
    r = client.post("/cart/add", data={"product_id":"robe_kabyle_2","qty":"1"}, follow_redirects=True)
    print("POST status:", r.status_code)
    with client.session_transaction() as sess:
        print("session cart:", sess.get("cart"))
        print("_flashes:", sess.get("_flashes"))
    r2 = client.get("/cart")
    print("/cart status:", r2.status_code)
    print(r2.get_data(as_text=True)[:400].replace("\n"," "))