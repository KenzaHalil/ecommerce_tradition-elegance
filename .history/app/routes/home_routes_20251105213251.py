from flask import Blueprint, render_template, current_app, url_for, request, flash, redirect
from werkzeug.routing import BuildError

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    return render_template("home.html")

@home_bp.route("/about")
def about():
    return render_template("about.html")

@home_bp.route("/contact", methods=["GET", "POST"])
def contact():
    # Handle contact form locally so it always shows the correct message.
    if request.method == "POST":
        # optionally read form fields: name = request.form.get("name")
        flash("Merci pour votre message !", "success")
        return redirect(url_for("home.contact"))

    # For GET: render the contact form pointing to this same route.
    action = url_for("home.contact")
    return render_template("contact.html", contact_action=action)