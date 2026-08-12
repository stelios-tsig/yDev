from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./ydev.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # παράγει μια νέα συνεδρία βάσης δεδομένων

Base = declarative_base()

def get_db():
    db= SessionLocal()
    try:
        yield db # Παράγει μια συνεδρία βάσης δεδομένων για χρήση σε ένα context manager.


    finally:
        db.close() # Το sesion κλείνει μετά την ολοκλήρωση της χρήσης του.

        
