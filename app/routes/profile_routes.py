from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from pathlib import Path
from app.models import User, db
import uuid
import os

profile_bp = Blueprint("profile", __name__)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@profile_bp.route("/profile", methods=["GET", "POST"])
def view_profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Veuillez vous connecter.", "warning")
        return redirect("/login")

    user = User.query.get(user_id)
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect("/")

    if request.method == "POST":
        f = request.files.get("profile_image")
        if f and f.filename:
            filename = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
            dest = UPLOAD_DIR / filename
            f.save(str(dest))  # write file to static/uploads
            user.profile_image = f"uploads/{filename}"  # store path usable by url_for('static', filename=...)
            db.session.commit()  # important
            flash("Photo de profil mise à jour.", "success")
            return redirect(url_for("profile.view_profile"))

    return render_template("profile.html", user=user)

@profile_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Veuillez vous connecter pour accéder à votre profil.", "warning")
        return redirect("/login")

    user = User.query.get(user_id)
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect("/")

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()

        f = request.files.get("profile_image")
        if f and f.filename:
            filename = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
            dest = UPLOAD_DIR / filename
            f.save(str(dest))
            user.profile_image = f"uploads/{filename}"

        db.session.commit()
        flash("Profil mis à jour.", "success")
        return redirect(url_for("profile.view_profile"))

    return render_template("edit_profile.html", user=user)