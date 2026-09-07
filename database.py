from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# `or` (όχι το default του getenv) ώστε και ένα ΚΕΝΟ string να πέφτει στο fallback.
SQLALCHEMY_DATABASE_URL = (os.getenv("DATABASE_URL") or "sqlite:///./ydev.db").strip().strip('"').strip("'")

# Μερικοί providers (Neon, Heroku) δίνουν "postgres://" — το SQLAlchemy θέλει "postgresql://".
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = "postgresql://" + SQLALCHEMY_DATABASE_URL[len("postgres://"):]

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # παράγει μια νέα συνεδρία βάσης δεδομένων

Base = declarative_base()

def get_db():
    db= SessionLocal()
    try:
        yield db # Παράγει μια συνεδρία βάσης δεδομένων για χρήση σε ένα context manager.


    finally:
        db.close() # Το sesion κλείνει μετά την ολοκλήρωση της χρήσης του.
