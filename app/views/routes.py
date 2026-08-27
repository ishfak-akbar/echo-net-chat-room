from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("views.chat_page"))
    return redirect(url_for("views.login_page"))


@views_bp.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("views.chat_page"))
    return render_template("login.html")


@views_bp.route("/chat")
@login_required
def chat_page():
    return render_template("chat.html")


@views_bp.route("/admin")
@login_required
def admin_page():
    if not current_user.is_admin:
        return redirect(url_for("views.chat_page"))
    return render_template("admin.html")