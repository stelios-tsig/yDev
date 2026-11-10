"""Ανέβασμα εικόνας project στο Cloudinary.

Τα tests κάνουν monkeypatch το `upload_image_to_cloudinary` ΣΕ ΑΥΤΟ το module
(services.images), γιατί εδώ γίνεται η κλήση.
"""
import os

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

import models
from cloud_utils import upload_image_to_cloudinary

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def validate_upload(file: UploadFile) -> None:
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Το UploadFile.file είναι ένα seekable αρχείο· βρίσκουμε το μέγεθος
    # χωρίς να διαβάσουμε ολόκληρο το περιεχόμενο στη μνήμη.
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be smaller than 5MB")


def attach_to_project(db: Session, project: models.Project, file: UploadFile) -> models.Project:
    validate_upload(file)
    project.image_url = upload_image_to_cloudinary(file.file, public_id=f"ydev/project_{project.id}")
    db.commit()
    db.refresh(project)
    return project
