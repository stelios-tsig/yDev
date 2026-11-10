"""Επαναφορά κωδικού: token μίας χρήσης με λήξη.

Τα tests κάνουν monkeypatch το `send_email` ΣΕ ΑΥΤΟ το module
(services.passwords), γιατί εδώ γίνεται η κλήση.
"""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import models
from email_utils import send_email

PASSWORD_RESET_TTL_HOURS = 1


def valid_token(db: Session, token_str: str) -> models.PasswordResetToken | None:
    token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token_str
    ).first()
    if not token or token.used:
        return None

    expires_at = token.expires_at
    if expires_at.tzinfo is None:  # SQLite επιστρέφει naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    return token


def send_reset_link(db: Session, user: models.User, base_url) -> None:
    reset = models.PasswordResetToken(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TTL_HOURS),
    )
    db.add(reset)
    db.commit()

    reset_link = f"{base_url}reset-password/{reset.token}"
    send_email(
        to=user.email,
        subject="yDev — Επαναφορά κωδικού",
        body=(
            f"Γεια σου {user.username},\n\n"
            f"Ζητήθηκε επαναφορά κωδικού για τον λογαριασμό σου. Άνοιξε τον παρακάτω σύνδεσμο "
            f"για να ορίσεις νέο κωδικό (λήγει σε {PASSWORD_RESET_TTL_HOURS} ώρα):\n\n"
            f"{reset_link}\n\n"
            f"Αν δεν το ζήτησες εσύ, αγνόησε αυτό το email."
        ),
    )


def consume(db: Session, reset: models.PasswordResetToken, new_password: str) -> None:
    from services import users as user_service

    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    reset.used = True
    user_service.set_password(db, user, new_password)
