"""REST: projects."""
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

import models
import schemas
from auth_utils import get_current_user
from database import get_db
from services import images as image_service
from services import projects as project_service

router = APIRouter(tags=["projects"])


@router.post("/projects/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return project_service.create(
        db,
        owner=current_user,
        title=project.title,
        description=project.description,
        category=project.category,
        github_url=project.github_url,
        technology_ids=project.technology_ids,
    )


@router.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return project_service.list_all(db, skip=skip, limit=limit)


# Το συγκεκριμένο GET δηλώνεται μετά το POST /projects/ επειδή το
# "/projects/{project_id}" θα έπιανε και άλλες διαδρομές.
@router.get("/projects/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    return project_service.get_or_404(db, project_id, with_relations=True)


@router.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project_update: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the project owner can edit this project")

    return project_service.update(
        db,
        project,
        title=project_update.title,
        description=project_update.description,
        category=project_update.category,
        github_url=project_update.github_url,
        technology_ids=project_update.technology_ids,
    )


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the project owner can delete this project")
    project_service.delete(db, project)


@router.post("/projects/{project_id}/upload-image/", response_model=schemas.Project)
def upload_project_image(
    project_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the project owner can upload images")
    return image_service.attach_to_project(db, project, file)
