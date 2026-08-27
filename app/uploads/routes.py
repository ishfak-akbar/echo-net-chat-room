import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.uploads.validation import validate_and_save_image, UploadError

uploads_bp = Blueprint("uploads", __name__, url_prefix="/uploads")


@uploads_bp.route("/dp", methods=["POST"])
@login_required
def upload_dp():
    file_storage = request.files.get("file")

    try:
        new_path = validate_and_save_image(file_storage, "dp")
    except UploadError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    old_path = current_user.profile_pic
    current_user.profile_pic = new_path
    db.session.commit()

    if old_path:
        _delete_old_static_file(old_path)

    return jsonify({"success": True, "profile_pic": new_path}), 200


@uploads_bp.route("/chat-image", methods=["POST"])
@login_required
def upload_chat_image():
    file_storage = request.files.get("file")

    try:
        image_url = validate_and_save_image(file_storage, "uploads/chat")
    except UploadError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({"success": True, "image_url": image_url}), 200


def _delete_old_static_file(relative_url: str) -> None:
    """Best-effort cleanup of a replaced profile picture. Never raises."""
    try:
        relative_path = relative_url.lstrip("/").split("static/", 1)[-1]
        full_path = os.path.join(current_app.static_folder, relative_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
    except Exception:
        pass