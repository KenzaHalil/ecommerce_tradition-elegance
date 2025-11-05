import re

def is_valid_address(address, city, postal_code):
    if not address or not city or not postal_code:
        return False, "Tous les champs d'adresse sont obligatoires."
    if not re.match(r"^\d{5}$", postal_code):
        return False, "Le code postal doit comporter 5 chiffres."
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]+$", city):
        return False, "La ville doit contenir uniquement des lettres."
    return True, ""

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        address = request.form["address"]
        city = request.form["city"]
        postal_code = request.form["postal_code"]

        valid, msg = is_valid_address(address, city, postal_code)
        if not valid:
            error = msg
        else:
            try:
                auth.register(email, password, first_name, last_name, address, city, postal_code)
                return redirect(url_for("auth.login"))
            except Exception as e:
                error = str(e)
    return render_template("register.html", error=error)