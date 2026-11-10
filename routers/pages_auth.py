"""Εγγραφή, σύνδεση, αποσύνδεση και επαναφορά κωδικού (σελίδες HTML)."""
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

import deps
from auth_utils import create_access_token
from database import get_db
from deps import templates
from rate_limit import rate_limit
from services import passwords as password_service
from services import users as user_service

router = APIRouter(tags=["pages"])


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


@router.post("/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    rate_limit(request, "register", max_calls=10, window_seconds=60)
    user_service.register(db, username=username, email=email, password=password)
    return deps.redirect("/login-page")


@router.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login-page")
def login_page_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    rate_limit(request, "login", max_calls=10, window_seconds=60)

    user = user_service.authenticate(db, username, password)
    if not user:
        # 200 με το μήνυμα μέσα στη σελίδα, ώστε η φόρμα να ξαναεμφανιστεί.
        return templates.TemplateResponse(
            request, "login.html", {"error": "Λάθος όνομα χρήστη ή κωδικός"},
        )

    response = deps.redirect("/home")
    deps.set_auth_cookie(response, create_access_token(data={"sub": str(user.id)}))
    return response


# Το logout αλλάζει κατάσταση, άρα δεν πρέπει να απαντά σε GET: prefetchers,
# επιταχυντές browser και antivirus μπορούν να ακολουθήσουν ένα GET μόνα τους
# και να αποσυνδέσουν τον χρήστη χωρίς να το ζητήσει.
@router.post("/logout")
def logout():
    response = deps.redirect("/home")
    deps.clear_auth_cookie(response)
    return response


@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html", {})


@router.post("/forgot-password")
def forgot_password_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    rate_limit(request, "forgot", max_calls=5, window_seconds=60)

    user = user_service.find_by_email(db, email)

    # Αν ο χρήστης υπάρχει, φτιάχνουμε token και στέλνουμε email. Σε κάθε
    # περίπτωση δείχνουμε το ίδιο μήνυμα ώστε να μην αποκαλύπτουμε ποια emails
    # είναι εγγεγραμμένα (user enumeration).
    if user:
        password_service.send_reset_link(db, user, request.base_url)

    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"message": "Αν υπάρχει λογαριασμός με αυτό το email, στάλθηκε σύνδεσμος επαναφοράς."},
    )


@router.get("/reset-password/{token}")
def reset_password_page(token: str, request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "reset_password.html",
        {"token": token, "valid": password_service.valid_token(db, token) is not None},
    )


@router.post("/reset-password/{token}")
def reset_password_submit(
    token: str,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    reset = password_service.valid_token(db, token)
    if not reset:
        return templates.TemplateResponse(
            request, "reset_password.html", {"token": token, "valid": False},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "valid": True, "error": "Ο κωδικός πρέπει να έχει τουλάχιστον 6 χαρακτήρες."},
        )

    password_service.consume(db, reset, password)
    return deps.redirect("/login-page")
