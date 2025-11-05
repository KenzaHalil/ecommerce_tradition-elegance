from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

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
    services = current_app.extensions["services"]
    auth = services["auth"]
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        try:
            user = auth.login(email, password)
        except Exception as e:
            flash(str(e), "danger")
            return redirect(url_for("auth.login"))
        session['user_id'] = user.id
        session['is_admin'] = bool(getattr(user, "is_admin", False))
        flash("Connecté.", "success")
        return redirect(url_for("home.index"))
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_email", None)
    flash("Déconnecté.", "info")
    return redirect(url_for("home.index"))