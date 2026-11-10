"""Το στήσιμο της εφαρμογής: mounts, χειρισμός σφαλμάτων, routers.

Η λογική ζει στα `services/` και τα endpoints στα `routers/`. Εδώ μένει μόνο
ό,τι αφορά την εφαρμογή συνολικά.
"""
import os

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from deps import templates
from routers import (
    api_comments,
    api_projects,
    api_ratings,
    api_technologies,
    api_users,
    api_versions,
    pages_auth,
    pages_comments,
    pages_profile,
    pages_projects,
    pages_technologies,
)

# Το schema της βάσης το διαχειρίζεται το Alembic (alembic upgrade head).
# Γι' αυτό δεν καλούμε models.Base.metadata.create_all εδώ.

# Ο φάκελος uploads πρέπει να υπάρχει πριν τον κάνουμε mount, αλλιώς το
# StaticFiles ρίχνει σφάλμα στο startup.
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


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


@app.get("/")
def read_root():
    return RedirectResponse(url="/home")


# health check για να ελέγχουμε εαν το API είναι up
@app.get("/health")
def health_check():
    return {"status": "ok"}


# Πρώτα το REST API και μετά οι σελίδες, όπως ήταν και η σειρά δήλωσης όσο
# όλα βρίσκονταν σε αυτό το αρχείο.
app.include_router(api_users.router)
app.include_router(api_technologies.router)
app.include_router(api_projects.router)
app.include_router(api_comments.router)
app.include_router(api_ratings.router)
app.include_router(api_versions.router)

app.include_router(pages_auth.router)
app.include_router(pages_projects.router)
app.include_router(pages_comments.router)
app.include_router(pages_profile.router)
app.include_router(pages_technologies.router)
