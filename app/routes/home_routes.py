from flask import Blueprint, render_template, current_app, url_for
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
    # default action
    action = url_for("home.index")
    if "newsletter" in current_app.blueprints:
        # try the expected endpoints, fallback gracefully
        try:
            action = url_for("newsletter.contact_submit")
        except BuildError:
            try:
                action = url_for("newsletter.subscribe")
            except BuildError:
                action = url_for("home.index")
    return render_template("contact.html", contact_action=action)