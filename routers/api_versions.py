"""REST: εκδόσεις."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from auth_utils import get_current_user
from database import get_db
from services import projects as project_service
from services import versions as version_service

router = APIRouter(tags=["versions"])


@router.post("/projects/{project_id}/versions/", response_model=schemas.Version)
def create_version(
    project_id: int,
    version: schemas.VersionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, version_service.OWNER_ONLY)
    return version_service.create(
        db,
        project_id=project_id,
        version_number=version.version_number,
        changelog=version.changelog,
    )


@router.get("/projects/{project_id}/versions/", response_model=List[schemas.Version])
def read_versions(project_id: int, db: Session = Depends(get_db)):
    return version_service.for_project(db, project_id)
