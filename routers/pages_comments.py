"""Σχόλια μέσα από τη σελίδα της δημοσίευσης.

Επεξεργασία: μόνο ο συντάκτης του σχολίου.
Διαγραφή: ο συντάκτης του σχολίου Ή ο ιδιοκτήτης της δημοσίευσης.
"""
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

import deps
import models
from database import get_db
from deps import templates
from services import comments as comment_service
from services import projects as project_service

router = APIRouter(tags=["pages"])


@router.post("/project/{project_id}/comment-submit")
def submit_comment_form(
    project_id: int,
    request: Request,
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    category_value = comment_service.parse_category(category)
    project_service.get_or_404(db, project_id)

    comment_service.create(
        db, project_id=project_id, user=current_user, content=content, category=category_value
    )
    return deps.redirect_to_project(project_id)


@router.get("/comment/{comment_id}/edit")
def edit_comment_page(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    comment = comment_service.get_or_404(db, comment_id)
    comment_service.require_author(comment, current_user)

    return templates.TemplateResponse(request, "edit_comment.html", {"comment": comment})


@router.post("/comment/{comment_id}/edit")
def edit_comment_submit(
    comment_id: int,
    request: Request,
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    comment = comment_service.get_or_404(db, comment_id)
    comment_service.require_author(comment, current_user)

    comment_service.update(
        db, comment, content=content, category=comment_service.parse_category(category)
    )
    return deps.redirect_to_project(comment.project_id)


@router.post("/comment/{comment_id}/delete")
def delete_comment_submit(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    comment = comment_service.get_or_404(db, comment_id)
    comment_service.require_author_or_project_owner(db, comment, current_user)

    project_id = comment.project_id
    comment_service.delete(db, comment)
    return deps.redirect_to_project(project_id)
