"""Διαχείριση τεχνολογιών (κάθε συνδεδεμένος χρήστης μπορεί να προσθέσει)."""
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

import deps
import models
from database import get_db
from deps import templates
from services import technologies as technology_service

router = APIRouter(tags=["pages"])


@router.get("/technologies-page")
def technologies_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    return templates.TemplateResponse(request, "technologies.html", {
        "current_user": current_user,
        "technologies": technology_service.list_all(db, ordered=True),
    })


@router.post("/technologies-page")
def technologies_add(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    technology_service.add_if_missing(db, name)
    return deps.redirect("/technologies-page")
