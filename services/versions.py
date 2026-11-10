"""Εκδόσεις ενός project."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

import models

OWNER_ONLY = "Only the project owner can add Versions"


def for_project(db: Session, project_id: int) -> list[models.Version]:
    return db.query(models.Version).filter(models.Version.project_id == project_id).all()


def create(db: Session, *, project_id: int, version_number: str, changelog: str | None) -> models.Version:
    version = models.Version(
        version_number=version_number,
        changelog=changelog,
        project_id=project_id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def clean_version_number(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Version number is required")
    return value
