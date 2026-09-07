from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request ,Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from typing import List
from auth_utils import hash_password, create_access_token, verify_password, get_current_user, get_current_user_from_cookie
import models
import os
import secrets
import schemas
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from cloud_utils import upload_image_to_cloudinary
from email_utils import send_email


# Το schema της βάσης το διαχειρίζεται πλέον το Alembic (alembic upgrade head).
# Γι' αυτό δεν καλούμε models.Base.metadata.create_all εδώ.

#Ο φάκελος uploads πρέπει να υπάρχει πριν τον κάνουμε mount αλλιώς το StaticFiles ρίχνει σφάλμα στο startup.
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
#Έυρεση αρχείου με το συγκεκριμένο όνομα στον φάκελο uploads.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
#Ιδια λογική
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Το cookie του JWT. SameSite=Lax μπλοκάρει cross-site POST (βασική προστασία
# CSRF). Secure μόνο σε production (HTTPS) — τοπικά μέσω http θα έσπαγε το login.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def set_auth_cookie(response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=1800,
    )


def normalize_email(value: str) -> str:
    """Τα emails αποθηκεύονται/συγκρίνονται πάντα πεζά και χωρίς κενά."""
    return value.strip().lower()


@app.exception_handler(StarletteHTTPException)
async def html_error_handler(request: Request, exc: StarletteHTTPException):
    """Για αιτήματα browser (403/404), δείξε σελίδα αντί για raw JSON."""
    wants_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code in (403, 404) and wants_html:
        return templates.TemplateResponse(
            request, "error.html",
            {"status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )
    return await http_exception_handler(request, exc)


#Ελεγχος διπλότυπου email---------------------------------------------------

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    email = normalize_email(user.email)
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail= "Email already registered")
    hashed_pw = hash_password(user.password)
    db_user= models.User(
        username=user.username,
        email=email,
        hashed_password= hashed_pw,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/")
def read_root():
    return RedirectResponse(url="/home")

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
@app.get("/projects/{project_id}", response_model= schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project: #Εαν δεν υπάρχει πρότζεκτ
        raise HTTPException(status_code=404, detail="Project not found")
    return project

#Λίστα προτζεκτ---------------------------------------------------------------------

@app.get("/projects/", response_model=List[schemas.Project])
def read_projects(skip:int = 0, limit: int = 100, db: Session= Depends(get_db)):
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

#login------------------------------------------------------------------------------

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
@app.get("/projects/{project_id}/comments/", response_model=List[schemas.Comment])
def read_comments(project_id: int, db: Session =Depends(get_db)):
    comments = db.query(models.Comment).filter(models.Comment.project_id == project_id).all()
    return comments

#Rating
@app.post("/projects/{project_id}/ratings/", response_model=schemas.Rating)
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
@app.post("/projects/{project_id}/versions/", response_model=schemas.Version)
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



#UPLOAD PHOTOS--------------------------------------------------

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def validate_image_upload(file: UploadFile) -> None:
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")

    #Το UploadFile.file είναι ένα seekable αρχείο· βρίσκουμε το μέγεθος
    #χωρίς να διαβάσουμε ολόκληρο το περιεχόμενο στη μνήμη.
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Image must be smaller than 5MB")


@app.post("/projects/{project_id}/upload-image/", response_model=schemas.Project)
def upload_project_image(
    project_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can upload images")

    validate_image_upload(file)
#V2.0
#Προηγούμενη έκδοση
    image_url = upload_image_to_cloudinary(file.file,public_id=f"ydev/project_{project_id}")
    project.image_url = image_url


    db.commit()
    db.refresh(project)
    return project        

#PUT------------------------------------------------------
@app.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project_update: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session =Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id ==project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can edit this project")

    project.title= project_update.title
    project.description = project_update.description
    project.category = project_update.category
    project.github_url = project_update.github_url

    if project_update.technology_ids:
        technologies = db.query(models.Technology).filter(
            models.Technology.id.in_(project_update.technology_ids)
        ).all()
        project.technologies = technologies
    else:
        project.technologies =[]

    db.commit()
    db.refresh(project)
    return project



#DELETE---------------------------------------------------
@app.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise   HTTPException(status_code=404, detail="Project not found")
    
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can delete this project")

    db.delete(project)
    db.commit()


#COMMENT EDIT

@app.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    current_user:models.User = Depends(get_current_user),
    db:Session = Depends(get_db),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    project = db.query(models.Project).filter(models.Project.id == comment.project_id).first()

    #Επιτρέπεται στον συντάκτη του σχολίου ή στον ιδιοκτήτη της δημοσίευσης.
    if comment.user_id != current_user.id and (project is None or project.owner_id != current_user.id):
        raise HTTPException(status_code=403,detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()


#Επεξεργασία σχολίου (μόνο ο συντάκτης).
@app.put("/comments/{comment_id}", response_model=schemas.Comment)
def update_comment(
    comment_id: int,
    comment_update: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the comment author can edit this comment")

    comment.content = comment_update.content
    comment.category = comment_update.category.value
    db.commit()
    db.refresh(comment)
    return comment


#PAGE description,comments,ratings,versions

@app.get("/project/{project_id}/page")
def project_detail_page(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    comments = db.query(models.Comment).filter(models.Comment.project_id == project_id).all()
    ratings = db.query(models.Rating).filter(models.Rating.project_id == project_id).all()
    versions = db.query(models.Version).filter(models.Version.project_id == project_id).all()

    average_rating = round(sum(r.stars for r in ratings) / len(ratings), 1) if ratings else None
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"),db=db)
    return templates.TemplateResponse(request, "project_detail.html", {
        "project": project,
        "comments": comments,
        "ratings": ratings,
        "versions": versions,
        "average_rating": average_rating,
        "current_user": current_user,
    })

#Εγγραφή χρήστη 
@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})

@app.post("/register")
def register_submit(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    email = normalize_email(email)
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(password)
    db_user = models.User(username=username, email=email, hashed_password= hashed_pw)
    db.add(db_user)
    db.commit()

    return RedirectResponse(url="/login-page",status_code=303)

@app.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.post("/login-page")
def login_page_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "Λάθος όνομα χρήστη ή κωδικός"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    response = RedirectResponse(url="/home", status_code=303)
    set_auth_cookie(response, access_token)
    return response

#Εμφάνιση σύνδεσης

PROJECTS_PER_PAGE = 9


@app.get("/home")
def home(
    request: Request,
    q: str = "",
    category: str = "",
    tech: int | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    q = q.strip()
    category = category.strip()

    query = db.query(models.Project)
    if q:
        query = query.filter(models.Project.title.ilike(f"%{q}%"))
    if category:
        query = query.filter(models.Project.category == category)
    if tech:
        query = query.filter(models.Project.technologies.any(models.Technology.id == tech))

    total = query.count()
    total_pages = max((total + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE, 1)
    page = min(max(page, 1), total_pages)

    projects = (
        query.order_by(models.Project.id.desc())
        .offset((page - 1) * PROJECTS_PER_PAGE)
        .limit(PROJECTS_PER_PAGE)
        .all()
    )

    #Επιλογές για τα dropdown φίλτρα.
    categories = [
        row[0]
        for row in db.query(models.Project.category).distinct().order_by(models.Project.category).all()
        if row[0]
    ]
    technologies = db.query(models.Technology).order_by(models.Technology.name).all()

    #Links pagination που κρατάνε τα ενεργά φίλτρα.
    active_filters = {k: v for k, v in (("q", q), ("category", category), ("tech", tech)) if v}

    def page_url(target_page: int) -> str:
        return "/home?" + urlencode({**active_filters, "page": target_page})

    prev_url = page_url(page - 1) if page > 1 else None
    next_url = page_url(page + 1) if page < total_pages else None

    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    return templates.TemplateResponse(
        request, "index.html", {
        "projects": projects,
        "current_user": current_user,
        "categories": categories,
        "technologies": technologies,
        "q": q,
        "selected_category": category,
        "selected_tech": tech,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "prev_url": prev_url,
        "next_url": next_url,
    })

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/home", status_code=303)
    response.delete_cookie("access_token", samesite="lax", secure=COOKIE_SECURE)
    return response

#Φόρμα δημιουργίας Project
@app.get("/create-project")
def create_project_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    technologies = db.query(models.Technology).all()
    return templates.TemplateResponse(request, "create_project.html", {
        "current_user": current_user,
        "technologies": technologies,
    })

@app.post("/create-project")
def create_project_submit(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    github_url: str = Form(""),
    technology_ids:list[int] = Form([]),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):

    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"),db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    db_project = models.Project(
        title=title,
        description= description,
        category= category,
        github_url= github_url,
        owner_id=current_user.id,

    )

    if technology_ids:
        technologies= db.query(models.Technology).filter(
            models.Technology.id.in_(technology_ids)
        ).all()
        db_project.technologies = technologies

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    if image and image.filename:
        validate_image_upload(image)
        image_url = upload_image_to_cloudinary(image.file, public_id=f"ydev/project_{db_project.id}")
        db_project.image_url=image_url
        db.commit()

    return RedirectResponse(url=f"/project/{db_project.id}/page", status_code=303)

#Φόρμα σχολίων στη σελίδα του project.
@app.post("/project/{project_id}/comment-submit")
def submit_comment_form(
    project_id: int,
    request: Request,
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user_from_cookie(access_token= request.cookies.get("access_token"),db=db)
    if not current_user:
        return RedirectResponse(url="/login-page",status_code=303)

    try:
        category_value = schemas.CommentCategory(category).value
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid comment category")

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_comment = models.Comment(
        content=content,
        category= category_value,
        project_id= project_id,
        user_id = current_user.id,

    )

    db.add(db_comment)
    db.commit()

    return RedirectResponse(url=f"/project/{project_id}/page", status_code=303)

#Φόρμα βαθμολόγησης

@app.post("/project/{project_id}/rating-submit")
def submit_rating_form(
    project_id: int,
    request: Request,
    stars: int = Form(...),
    db: Session = Depends(get_db),

):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"),db=db)
    if not current_user:
        return RedirectResponse(url="/login-page",status_code=303)

    if stars < 1 or stars > 5:
        raise HTTPException(status_code=422, detail="Stars must be between 1 and 5")

    project = db.query(models.Project).filter(models.Project.id ==project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    #Εαν ο χρήστης έχει ήδη βαθμολογήσει, ενημερώνουμε την υπάρχουσα βαθμολογία.
    existing_rating = db.query(models.Rating).filter(
        models.Rating.project_id == project_id,
        models.Rating.user_id == current_user.id,
    ).first()

    if existing_rating:
        existing_rating.stars = stars
    else:
        db.add(models.Rating(stars=stars, project_id=project_id, user_id=current_user.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

    return RedirectResponse(url=f"/project/{project_id}/page",status_code=303)


#Edit

@app.get("/project/{project_id}/edit")
def edit_project_page(project_id: int, request: Request, db: Session= Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can edit this project")

    technologies = db.query(models.Technology).all()
    selected_ids = {tech.id for tech in project.technologies}

    return templates.TemplateResponse(request, "edit_project.html",{
        "project": project,
        "technologies": technologies,
        "selected_ids" :selected_ids,
    })

@app.post("/project/{project_id}/edit")
def edit_project_submit(
    project_id:int,
    request: Request,
    title: str= Form(...),
    description: str = Form(""),
    category: str = Form(...),
    github_url: str = Form(""),
    technology_ids: list[int]= Form([]),
    db: Session = Depends(get_db),
):
    current_user = get_current_user_from_cookie(access_token= request.cookies.get("access_token"),db=db)
    if not current_user:
        return RedirectResponse(url="/login-page",status_code=303)

    project = db.query(models.Project).filter(models.Project.id== project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can edit this project")

    project.title= title
    project.description = description
    project.category = category
    project.github_url = github_url

    if technology_ids:
        technologies = db.query(models.Technology).filter(
            models.Technology.id.in_(technology_ids)
        ).all()
        project.technologies = technologies
    else:
        project.technologies = []

    db.commit()
    return RedirectResponse(url=f"/project/{project_id}/page", status_code=303)

#Edit (DELETE)

@app.post("/project/{project_id}/delete")
def delete_project_submit(project_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this project")


    db.delete(project)
    db.commit()

    return RedirectResponse(url="/home", status_code=303)


#Σχόλια — επεξεργασία / διαγραφή μέσα από τη σελίδα της δημοσίευσης
#Επεξεργασία: μόνο ο συντάκτης του σχολίου.
#Διαγραφή: ο συντάκτης του σχολίου Ή ο ιδιοκτήτης της δημοσίευσης.

@app.get("/comment/{comment_id}/edit")
def edit_comment_page(comment_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the comment author can edit this comment")

    return templates.TemplateResponse(request, "edit_comment.html", {
        "comment": comment,
    })


@app.post("/comment/{comment_id}/edit")
def edit_comment_submit(
    comment_id: int,
    request: Request,
    content: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the comment author can edit this comment")

    try:
        category_value = schemas.CommentCategory(category).value
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid comment category")

    comment.content = content
    comment.category = category_value
    db.commit()

    return RedirectResponse(url=f"/project/{comment.project_id}/page", status_code=303)


@app.post("/comment/{comment_id}/delete")
def delete_comment_submit(comment_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    project = db.query(models.Project).filter(models.Project.id == comment.project_id).first()

    if comment.user_id != current_user.id and (project is None or project.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    project_id = comment.project_id
    db.delete(comment)
    db.commit()

    return RedirectResponse(url=f"/project/{project_id}/page", status_code=303)


#Προφίλ χρήστη (δημόσιο) + επεξεργασία bio (μόνο ο ίδιος ο χρήστης)

@app.get("/user/{user_id}/page")
def user_profile_page(user_id: int, request: Request, db: Session = Depends(get_db)):
    profile_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not profile_user:
        raise HTTPException(status_code=404, detail="User not found")

    projects = db.query(models.Project).filter(models.Project.owner_id == user_id).order_by(models.Project.id.desc()).all()
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)

    return templates.TemplateResponse(request, "user_profile.html", {
        "profile_user": profile_user,
        "projects": projects,
        "current_user": current_user,
    })


@app.get("/profile/edit")
def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    return templates.TemplateResponse(request, "edit_profile.html", {
        "current_user": current_user,
    })


@app.post("/profile/edit")
def edit_profile_submit(
    request: Request,
    bio: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user_from_cookie(access_token=request.cookies.get("access_token"), db=db)
    if not current_user:
        return RedirectResponse(url="/login-page", status_code=303)

    current_user.bio = bio or None
    db.commit()

    return RedirectResponse(url=f"/user/{current_user.id}/page", status_code=303)


#Επαναφορά κωδικού ("ξέχασα τον κωδικό")

PASSWORD_RESET_TTL_HOURS = 1


def _valid_reset_token(token_str: str, db: Session) -> models.PasswordResetToken | None:
    token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == token_str
    ).first()
    if not token or token.used:
        return None

    expires_at = token.expires_at
    if expires_at.tzinfo is None:  # SQLite επιστρέφει naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    return token


@app.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html", {})


@app.post("/forgot-password")
def forgot_password_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    email = normalize_email(email)
    # func.lower ώστε να ταιριάζει και με παλιές εγγραφές που αποθηκεύτηκαν με κεφαλαία.
    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()

    #Αν ο χρήστης υπάρχει, φτιάχνουμε token και στέλνουμε email. Σε κάθε
    #περίπτωση δείχνουμε το ίδιο μήνυμα ώστε να μην αποκαλύπτουμε ποια emails
    #είναι εγγεγραμμένα (user enumeration).
    if user:
        reset = models.PasswordResetToken(
            token=secrets.token_urlsafe(32),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TTL_HOURS),
        )
        db.add(reset)
        db.commit()

        reset_link = f"{request.base_url}reset-password/{reset.token}"
        send_email(
            to=user.email,
            subject="yDev — Επαναφορά κωδικού",
            body=(
                f"Γεια σου {user.username},\n\n"
                f"Ζητήθηκε επαναφορά κωδικού για τον λογαριασμό σου. Άνοιξε τον παρακάτω σύνδεσμο "
                f"για να ορίσεις νέο κωδικό (λήγει σε {PASSWORD_RESET_TTL_HOURS} ώρα):\n\n"
                f"{reset_link}\n\n"
                f"Αν δεν το ζήτησες εσύ, αγνόησε αυτό το email."
            ),
        )

    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"message": "Αν υπάρχει λογαριασμός με αυτό το email, στάλθηκε σύνδεσμος επαναφοράς."},
    )


@app.get("/reset-password/{token}")
def reset_password_page(token: str, request: Request, db: Session = Depends(get_db)):
    valid = _valid_reset_token(token, db) is not None
    return templates.TemplateResponse(
        request, "reset_password.html",
        {"token": token, "valid": valid},
    )


@app.post("/reset-password/{token}")
def reset_password_submit(
    token: str,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    reset = _valid_reset_token(token, db)
    if not reset:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "valid": False},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"token": token, "valid": True, "error": "Ο κωδικός πρέπει να έχει τουλάχιστον 6 χαρακτήρες."},
        )

    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    user.hashed_password = hash_password(password)
    reset.used = True
    db.commit()

    return RedirectResponse(url="/login-page", status_code=303)