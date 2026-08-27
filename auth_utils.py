import os
from passlib.context import CryptContext
from datetime import datetime, timedelta,timezone
from dotenv import load_dotenv
from jose import jwt, JWTError
from fastapi import Depends,HTTPException,status, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models


# Διαβάζει το αρχείο .env και φορτώνει τις τιμές του μέσα στις 
# environment variables του τρέχοντος process , σαν να τις είχες ορίσει στο ίδιο 
# το λειτουργικό σύστημα
load_dotenv()

pwd_context = CryptContext (schemes = ["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

#Διαβάσζει την τιμή την environment variable με το συγκεκριμένο όνομα που μόλις φορτώθηκε από το .Env
#Εάν λείπει το κλειδί ή το env επιστρέφει None.
SECRET_KEY = os.getenv("SECRET_KEY")
#Αλγόριθμος κρυπτογράφησης που θα χρησιμοποιηθεί για την υπογραφή.
ALGORITHM= "HS256"
#Χρόνος λειτουργείας token πριν λήξει.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    #Δέχεται αντίγραφο του dictionary που δώθηκε για να μην τροποποιήσουμε κατά λάθος το αρχικό object.
    to_encode = data.copy() 
    #Υπολογισμός λήξης token και προσθέτουμε payload με κλειδί "exp"(expiration)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    #Από εδώ και πέρα το jwt.to_encode υπογράφει με SECRET_KEY χρησιμοποιώντας τον αλγόριθμο HS256
    #και επιστρέφει το τελικό σφραγισμένο token ως string
    to_encode.update({"exp":expire})
    encoded_jwt =jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


#-----------------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db:Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate crementials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id:str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id ==int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

#Cookie

def get_current_user_from_cookie(access_token: str = Cookie(None), db: Session = Depends(get_db)):
    print("DEBUG: access_token =", access_token)
    if access_token is None:
        print("DEBUG: no token found")
        return None

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        print("DEBUG: decoded user_id =", user_id)
        if user_id is None:
            return None
    except JWTError as e:
        print("DEBUG: JWTError:", e)
        return None

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    print("DEBUG: found user =", user)
    return user