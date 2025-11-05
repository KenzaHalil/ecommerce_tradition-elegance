from flask import Blueprint, request, redirect, url_for, flash, render_template

newsletter_bp = Blueprint("newsletter", __name__)

@newsletter_bp.route("/newsletter", methods=["POST"])
def subscribe():
    email = request.form["email"]
    # Ajoute l'email à la base ou fichier
    flash("Merci pour votre inscription à la newsletter !", "success")
    return redirect(url_for("home.index"))

