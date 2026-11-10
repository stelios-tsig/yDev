"""REST: τεχνολογίες."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import schemas
from database import get_db
from services import technologies as technology_service

router = APIRouter(tags=["technologies"])


@router.post("/technologies/", response_model=schemas.Technology)
def create_technology(technology: schemas.TechnologyCreate, db: Session = Depends(get_db)):
    return technology_service.create(db, technology.name)


@router.get("/technologies/", response_model=List[schemas.Technology])
def read_technologies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return technology_service.list_all(db, skip=skip, limit=limit)
