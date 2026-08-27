import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app


class UploadError(Exception):
    pass


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_and_save_image(file_storage, destination_folder: str) -> str:
    if not file_storage or not file_storage.filename:
        raise UploadError("No file provided.")

    original_name = secure_filename(file_storage.filename)
    ext = _extension(original_name)

    allowed = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    if ext not in allowed:
        raise UploadError(
            f"File type '.{ext}' is not allowed. Allowed: {', '.join(sorted(allowed))}."
        )

    # Defense in depth: re-check size even though Flask's MAX_CONTENT_LENGTH
    # already rejects oversized requests before this code runs.
    file_storage.stream.seek(0, os.SEEK_END)
    size_bytes = file_storage.stream.tell()
    file_storage.stream.seek(0)

    max_bytes = current_app.config["MAX_CONTENT_LENGTH"]
    if max_bytes and size_bytes > max_bytes:
        raise UploadError("File is too large.")

    # Verify the content is genuinely a valid image, not just a renamed file
    # with a fake extension (e.g. a script named photo.png).
    try:
        image = Image.open(file_storage.stream)
        image.verify()
    except Exception:
        raise UploadError("File is not a valid image.")

    file_storage.stream.seek(0)

    static_root = current_app.static_folder
    save_dir = os.path.join(static_root, destination_folder)
    os.makedirs(save_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(save_dir, unique_name)
    file_storage.save(save_path)

    return f"/static/{destination_folder}/{unique_name}"