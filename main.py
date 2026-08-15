from fastapi import FastAPI, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db
from typing import List
from auth_utils import hash_password
import models
import schemas



models.Base.metadata.create_all(bind=engine)

app = FastAPI()

#Ελεγχος διπλότυπου email

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail= "Email already registered")
    hashed_pw = hash_password(user.password)
    db_user= models.User(
        username=user.username,
        email=user.email,
        hashed_password= hashed_pw,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/")
def read_root():
    return {"message": "yDev. Welcome!"}

#Δημιουργία ενός νέου τεχνολογικού αντικειμένου
#Δοκιμή με χρήση του FastAPI και SQLAlchemy για την αποθήκευση ενός νέου αντικειμένου τεχνολογίας στη βάση δεδομένων.

@app.post("/technologies/", response_model=schemas.Technology)
def create_technology(technology: schemas.TechnologyCreate, db: Session = Depends(get_db)):
    db_technology = models.Technology(name=technology.name)
    db.add(db_technology)
    db.commit()
    db.refresh(db_technology)
    return db_technology

@app.get("/technologies/", response_model=List[schemas.Technology])
def read_technologies(skip: int = 0, limit: int = 100, db:Session = Depends(get_db)):
    technologies = db.query(models.Technology).offset(skip).limit(limit).all()
    return technologies


@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, owner_id: int, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    db_project = models.Project(
        title=project.title,
        description=project.description,
        category=project.category,
        github_url=project.github_url,
        owner_id=owner_id,
    )

    if project.technology_ids:
        technologies = db.query(models.Technology).filter(
            models.Technology.id.in_(project.technology_ids)
        ).all()
        db_project.technologies = technologies

    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project