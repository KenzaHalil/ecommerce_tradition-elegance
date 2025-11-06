home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    return render_template("home.html")

@home_bp.route("/about")
def about():
    return render_template("about.html")

@home_bp.route("/contact", methods=["GET", "POST"])
def contact():
    # If POST: handle the contact form locally and show the correct message
    if request.method == "POST":
        # you can read form fields if needed: name = request.form.get("name")
        flash("Merci pour votre message !", "success")
        return redirect(url_for("home.contact"))

    # For GET: the form action will point to this same route (avoid newsletter takeover)
    action = url_for("home.contact")
    return render_template("contact.html", contact_action=action)