from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    services = current_app.extensions["services"]
    auth = services["auth"]
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        if not email or not password:
            flash("Email et mot de passe requis.", "danger")
            return redirect(url_for("auth.register"))
        try:
            auth.register(email, password, first_name=first_name, last_name=last_name)
        except Exception as e:
            flash(str(e), "danger")
            return redirect(url_for("auth.register"))
        flash("Compte créé. Connecte-toi.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email")
    password = request.form.get("password")
    if not email or not password:
        flash("Email et mot de passe requis.", "danger")
        return redirect(url_for("auth.login"))

    services = current_app.extensions.get("services", {})
    auth = services.get("auth")
    if not auth:
        flash("Service d'authentification indisponible.", "danger")
        return redirect(url_for("auth.login"))

    try:
        res = auth.login(email, password)
    except Exception:
        current_app.logger.exception("Erreur d'authentification")
        flash("Erreur d'authentification.", "danger")
        return redirect(url_for("auth.login"))

    if not res:
        flash("Identifiants invalides.", "danger")
        return redirect(url_for("auth.login"))

    # res peut être {'user': {...}} ou l'utilisateur directement
    user = res.get("user") if isinstance(res, dict) else res

    # gérer user en dict ou en objet
    if isinstance(user, dict):
        uid = user.get("id")
        is_admin = bool(user.get("is_admin"))
    else:
        uid = getattr(user, "id", None)
        is_admin = bool(getattr(user, "is_admin", False))

    if not uid:
        flash("Erreur interne: utilisateur non valide.", "danger")
        return redirect(url_for("auth.login"))

    session["user_id"] = uid
    session["is_admin"] = bool(is_admin)

    flash("Connecté.", "success")
    next_url = request.args.get("next") or url_for("catalogue.catalogue")
    return redirect(next_url)

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_email", None)
    flash("Déconnecté.", "info")
    return redirect(url_for("home.index"))