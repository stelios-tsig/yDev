"""REST: βαθμολογίες."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from auth_utils import get_current_user
from database import get_db
from services import projects as project_service
from services import ratings as rating_service

router = APIRouter(tags=["ratings"])


@router.post("/projects/{project_id}/ratings/", response_model=schemas.Rating)
def create_rating(
    project_id: int,
    rating: schemas.RatingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project_service.get_or_404(db, project_id)
    rating_service.validate_stars(rating.stars)
    return rating_service.create(db, project_id=project_id, user=current_user, stars=rating.stars)


@router.get("/projects/{project_id}/ratings/", response_model=List[schemas.Rating])
def read_ratings(project_id: int, db: Session = Depends(get_db)):
    return rating_service.for_project(db, project_id, with_user=True)
