"""REST: εγγραφή και έκδοση token."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import schemas
from auth_utils import create_access_token
from database import get_db
from rate_limit import rate_limit
from services import users as user_service

router = APIRouter(tags=["users"])


@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Το schemas.User κρατάει το email: η απάντηση αφορά τον ίδιο τον χρήστη
    # που μόλις δημιουργήθηκε, όχι τρίτους.
    return user_service.register(
        db, username=user.username, email=user.email, password=user.password
    )


@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    rate_limit(request, "login", max_calls=10, window_seconds=60)

    user = user_service.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    return {"access_token": create_access_token(data={"sub": str(user.id)}), "token_type": "bearer"}
