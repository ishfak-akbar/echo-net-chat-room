from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User
from app.auth.validation import validate_username, validate_password

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _get_payload():
    """Accepts either JSON body or form-encoded data."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = _get_payload()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    username_error = validate_username(username)
    if username_error:
        return jsonify({"success": False, "message": username_error}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"success": False, "message": password_error}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "Username already taken."}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({"success": True, "user": user.to_public_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = _get_payload()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()

    # Deliberately vague error — never reveal whether the username exists
    invalid_creds = jsonify({"success": False, "message": "Invalid username or password."})

    if not user or not user.check_password(password):
        return invalid_creds, 401

    login_user(user, remember=True)
    user.touch_last_seen()
    db.session.commit()

    return jsonify({"success": True, "user": user.to_public_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"success": True, "user": current_user.to_public_dict()}), 200