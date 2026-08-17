from fastapi import FastAPI, Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import engine, get_db
from typing import List
from auth_utils import hash_password, create_access_token,verify_password
import models
import schemas
from auth_utils import get_current_user


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



#Project Creation--------------------------------------------------------------------------------
@app.post("/projects/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_project = models.Project(
        title=project.title,
        description=project.description,
        category=project.category,
        github_url=project.github_url,
        owner_id=current_user.id,
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




#Ελεγχός Project
#Το συγκεκριμένο GET πρέπει να λειτουργεί μετά το POST διότι η λειτουργία του γίνεται με αυτό και όχι παράλληλα.
@app.get("/projects{project_id}", response_model= schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project: #Εαν δεν υπάρχει πρότζεκτ
        raise HTTPException(status_code=404, detail="Project not found")
    return project

#Λίστα προτζεκτ

@app.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip:int = 0, limit: int = 100, db: Session= Depends(get_db)):
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

#login

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm =Depends(), db:Session= Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

#Comments in Projects
@app.post("/projects/{project_id}/comments/", response_model =schemas.Comment)
def create_comment(
    project_id: int,
    comment: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
#Ελεγχος εάν υπάρχει το project.
    project= db.query(models.Project).filter(models.Project.id== project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_comment = models.Comment(
        content= comment.content,
        category= comment.category.value,
        project_id=project_id,
        user_id= current_user.id,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


#Comments
@app.get("/projects/{project_id}/comment/", response_model=List[schemas.Comment])
def read_comments(project_id: int, db: Session =Depends(get_db)):
    comments = db.query(models.Comment).filter(models.Comment.project_id == project_id).all()
    return comments

#Rating
@app.post("/projects/{project_id}/rating/", response_model=schemas.Rating)
def create_rating(
    project_id: int,
    rating: schemas.RatingCreate,
    current_user: models.User= Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if rating.stars <1 or rating.stars > 5:
        raise HTTPException(status_code= 422, detail="Stars must be between 1 and 5 ")

    db_rating = models.Rating(
        stars=rating.stars,
        project_id= project_id,
        user_id= current_user.id,

    )
    db.add(db_rating)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You have already rated this project")

    db.refresh(db_rating)
    return db_rating

@app.get("/projects/{project_id}/ratings/", response_model=List[schemas.Rating])
def read_ratings(project_id: int, db: Session = Depends(get_db)):
    ratings = db.query(models.Rating).filter(models.Rating.project_id == project_id).all()
    return ratings


#Εκδοχες (versions)----------------------------
@app.post("/project/{project_id}/version/", response_model=schemas.Version)
def create_version(
    project_id: int,
    version: schemas.VersionCreate,
    current_user: models.User=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

#Ελεγχος ιδιοκτησίας-----------------------
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can add Versions")
        
    db_version = models.Version(
        version_number= version.version_number,
        changelog = version.changelog,
        project_id= project_id,
    )

    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version

@app.get("/projects/{project_id}/versions/", response_model=List[schemas.Version])
def read_versions(project_id: int, db: Session = Depends(get_db)):
    versions= db.query(models.Version).filter(models.Version.project_id== project_id).all()
    return versions