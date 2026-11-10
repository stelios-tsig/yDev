"""Σχόλια: δικαιώματα συντάκτη/ιδιοκτήτη και έλεγχος κατηγορίας."""
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas


def get_or_404(db: Session, comment_id: int) -> models.Comment:
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


def parse_category(value: str) -> str:
    """Το API το επικυρώνει το pydantic· οι φόρμες στέλνουν σκέτο string."""
    try:
        return schemas.CommentCategory(value).value
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid comment category")


def for_project(db: Session, project_id: int) -> list[models.Comment]:
    # Και το API και το template δείχνουν τον συντάκτη κάθε σχολίου.
    return (
        db.query(models.Comment)
        .options(joinedload(models.Comment.user))
        .filter(models.Comment.project_id == project_id)
        .all()
    )


def require_author(comment: models.Comment, user: models.User) -> None:
    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the comment author can edit this comment")


def require_author_or_project_owner(db: Session, comment: models.Comment, user: models.User) -> None:
    """Διαγραφή: ο συντάκτης του σχολίου Ή ο ιδιοκτήτης της δημοσίευσης."""
    if comment.user_id == user.id:
        return

    project = db.query(models.Project).filter(models.Project.id == comment.project_id).first()
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")


def create(db: Session, *, project_id: int, user: models.User, content: str, category: str) -> models.Comment:
    comment = models.Comment(
        content=content,
        category=category,
        project_id=project_id,
        user_id=user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def update(db: Session, comment: models.Comment, *, content: str, category: str) -> models.Comment:
    comment.content = content
    comment.category = category
    db.commit()
    db.refresh(comment)
    return comment


def delete(db: Session, comment: models.Comment) -> None:
    db.delete(comment)
    db.commit()
