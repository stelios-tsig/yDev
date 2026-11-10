"""Η κοινή ταξινομία τεχνολογιών."""
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models


def list_all(db: Session, *, ordered: bool = False, skip: int = 0, limit: int | None = None):
    query = db.query(models.Technology)
    if ordered:
        query = query.order_by(models.Technology.name)
    if skip:
        query = query.offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def create(db: Session, name: str) -> models.Technology:
    technology = models.Technology(name=name)
    db.add(technology)
    db.commit()
    db.refresh(technology)
    return technology


def add_if_missing(db: Session, name: str) -> None:
    """Σιωπηλά αγνοεί κενά και διπλότυπα — η φόρμα δεν εμφανίζει σφάλμα."""
    name = name.strip()
    if not name:
        return

    exists = db.query(models.Technology).filter(func.lower(models.Technology.name) == name.lower()).first()
    if exists:
        return

    db.add(models.Technology(name=name))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def by_ids(db: Session, technology_ids) -> list[models.Technology]:
    if not technology_ids:
        return []
    return db.query(models.Technology).filter(models.Technology.id.in_(technology_ids)).all()
