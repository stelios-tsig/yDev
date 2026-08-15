from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import models
import schemas
from database import engine, get_db
from typing import List

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


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