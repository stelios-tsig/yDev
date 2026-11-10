"""Ό,τι μοιράζονται τα routers: templates, cookie, τρέχων χρήστης.

Το `main.py` κρατάει μόνο το στήσιμο της εφαρμογής· αυτά εδώ τα χρειάζονται
σχεδόν όλα τα routers, οπότε ζουν χωριστά για να μην υπάρχει κυκλική εισαγωγή
(main -> routers -> main).
"""
import os

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from auth_utils import get_current_user_from_cookie
from database import get_db

templates = Jinja2Templates(directory="templates")

# Το cookie του JWT. SameSite=Lax μπλοκάρει cross-site POST (βασική προστασία
# CSRF). Secure μόνο σε production (HTTPS) — τοπικά μέσω http θα έσπαγε το login.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=1800,
    )


def clear_auth_cookie(response) -> None:
    response.delete_cookie("access_token", samesite="lax", secure=COOKIE_SECURE)


def optional_user(request: Request, db: Session = Depends(get_db)) -> models.User | None:
    """Ο συνδεδεμένος χρήστης, ή None.

    Οι σελίδες HTML διαβάζουν την ταυτότητα από το cookie και όχι από header
    Authorization, γι' αυτό δεν χρησιμοποιούν το get_current_user του API.
    """
    return get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)


CurrentUser = Depends(optional_user)


def redirect(url: str) -> RedirectResponse:
    """303 ώστε ο browser να ακολουθήσει με GET μετά από POST."""
    return RedirectResponse(url=url, status_code=303)


def redirect_to_login() -> RedirectResponse:
    return redirect("/login-page")


def redirect_to_project(project_id: int) -> RedirectResponse:
    return redirect(f"/project/{project_id}/page")
