"""Λογαριασμοί: εγγραφή και έλεγχος στοιχείων."""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from auth_utils import hash_password, verify_password


def normalize_email(value: str) -> str:
    """Τα emails αποθηκεύονται/συγκρίνονται πάντα πεζά και χωρίς κενά."""
    return value.strip().lower()


def find_by_email(db: Session, email: str) -> models.User | None:
    """func.lower ώστε να ταιριάζει και με παλιές εγγραφές με κεφαλαία."""
    return db.query(models.User).filter(func.lower(models.User.email) == normalize_email(email)).first()


def register(db: Session, *, username: str, email: str, password: str) -> models.User:
    """Νέος λογαριασμός. 400 αν το email χρησιμοποιείται ήδη."""
    email = normalize_email(email)
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(username=username, email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def set_password(db: Session, user: models.User, password: str) -> None:
    user.hashed_password = hash_password(password)
    db.commit()
