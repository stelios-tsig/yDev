"""Βαθμολογίες.

Οι δύο επιφάνειες έχουν σκόπιμα διαφορετική πολιτική στο διπλό ψήφο: το API
απαντά 400 (η δημιουργία απέτυχε), ενώ η φόρμα της σελίδας ενημερώνει την
υπάρχουσα βαθμολογία, γιατί ο χρήστης απλώς ξαναπάτησε αστεράκι. Η διαφορά
είναι εδώ ρητή, σε δύο ονομασμένες συναρτήσεις, αντί για δύο υλοποιήσεις που
έμοιαζαν ίδιες.
"""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

import models


def validate_stars(stars: int) -> None:
    if stars < 1 or stars > 5:
        raise HTTPException(status_code=422, detail="Stars must be between 1 and 5")


def for_project(db: Session, project_id: int, *, with_user: bool = False) -> list[models.Rating]:
    query = db.query(models.Rating)
    if with_user:
        query = query.options(joinedload(models.Rating.user))
    return query.filter(models.Rating.project_id == project_id).all()


def average(ratings) -> float | None:
    if not ratings:
        return None
    return round(sum(r.stars for r in ratings) / len(ratings), 1)


def create(db: Session, *, project_id: int, user: models.User, stars: int) -> models.Rating:
    """API: δεύτερη βαθμολογία από τον ίδιο χρήστη είναι σφάλμα."""
    rating = models.Rating(stars=stars, project_id=project_id, user_id=user.id)
    db.add(rating)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You have already rated this project")

    db.refresh(rating)
    return rating


def upsert(db: Session, *, project_id: int, user: models.User, stars: int) -> None:
    """Φόρμα: δεύτερη βαθμολογία αντικαθιστά την προηγούμενη."""
    existing = db.query(models.Rating).filter(
        models.Rating.project_id == project_id,
        models.Rating.user_id == user.id,
    ).first()

    if existing:
        existing.stars = stars
    else:
        db.add(models.Rating(stars=stars, project_id=project_id, user_id=user.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
