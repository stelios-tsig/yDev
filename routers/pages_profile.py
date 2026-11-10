"""Προφίλ χρήστη (δημόσιο) και επεξεργασία bio."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

import deps
import models
from database import get_db
from deps import templates
from services import projects as project_service

router = APIRouter(tags=["pages"])


@router.get("/user/{user_id}/page")
def user_profile_page(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    profile_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not profile_user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(request, "user_profile.html", {
        "profile_user": profile_user,
        "projects": project_service.owned_by(db, user_id),
        "current_user": current_user,
    })


@router.get("/profile/edit")
def edit_profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    return templates.TemplateResponse(request, "edit_profile.html", {"current_user": current_user})


@router.post("/profile/edit")
def edit_profile_submit(
    request: Request,
    bio: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    current_user.bio = bio or None
    db.commit()

    return deps.redirect(f"/user/{current_user.id}/page")
