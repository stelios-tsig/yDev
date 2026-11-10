"""REST: σχόλια."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from auth_utils import get_current_user
from database import get_db
from services import comments as comment_service
from services import projects as project_service

router = APIRouter(tags=["comments"])


@router.post("/projects/{project_id}/comments/", response_model=schemas.Comment)
def create_comment(
    project_id: int,
    comment: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project_service.get_or_404(db, project_id)
    return comment_service.create(
        db,
        project_id=project_id,
        user=current_user,
        content=comment.content,
        category=comment.category.value,
    )


@router.get("/projects/{project_id}/comments/", response_model=List[schemas.Comment])
def read_comments(project_id: int, db: Session = Depends(get_db)):
    return comment_service.for_project(db, project_id)


@router.put("/comments/{comment_id}", response_model=schemas.Comment)
def update_comment(
    comment_id: int,
    comment_update: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = comment_service.get_or_404(db, comment_id)
    comment_service.require_author(comment, current_user)
    return comment_service.update(
        db, comment, content=comment_update.content, category=comment_update.category.value
    )


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = comment_service.get_or_404(db, comment_id)
    comment_service.require_author_or_project_owner(db, comment, current_user)
    comment_service.delete(db, comment)
