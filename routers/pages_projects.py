"""Σελίδες HTML για projects: λίστα, προβολή, δημιουργία, επεξεργασία."""
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

import deps
import models
from database import get_db
from deps import templates
from services import comments as comment_service
from services import images as image_service
from services import projects as project_service
from services import ratings as rating_service
from services import technologies as technology_service
from services import versions as version_service

router = APIRouter(tags=["pages"])


@router.get("/home")
def home(
    request: Request,
    q: str = "",
    category: str = "",
    tech: int | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    q = q.strip()
    category = category.strip()

    projects, page, total_pages, total = project_service.search(
        db, q=q, category=category, tech=tech, page=page
    )

    # Links pagination που κρατάνε τα ενεργά φίλτρα.
    active_filters = {k: v for k, v in (("q", q), ("category", category), ("tech", tech)) if v}

    def page_url(target_page: int) -> str:
        return "/home?" + urlencode({**active_filters, "page": target_page})

    return templates.TemplateResponse(request, "index.html", {
        "projects": projects,
        "current_user": current_user,
        "categories": project_service.distinct_categories(db),
        "technologies": technology_service.list_all(db, ordered=True),
        "q": q,
        "selected_category": category,
        "selected_tech": tech,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "prev_url": page_url(page - 1) if page > 1 else None,
        "next_url": page_url(page + 1) if page < total_pages else None,
    })


@router.get("/project/{project_id}/page")
def project_detail_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    project = project_service.get_or_404(db, project_id, with_relations=True)
    ratings = rating_service.for_project(db, project_id)

    return templates.TemplateResponse(request, "project_detail.html", {
        "project": project,
        "comments": comment_service.for_project(db, project_id),
        "ratings": ratings,
        "versions": version_service.for_project(db, project_id),
        "average_rating": rating_service.average(ratings),
        "current_user": current_user,
    })


@router.get("/create-project")
def create_project_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    return templates.TemplateResponse(request, "create_project.html", {
        "current_user": current_user,
        "technologies": technology_service.list_all(db),
    })


@router.post("/create-project")
def create_project_submit(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    github_url: str = Form(""),
    technology_ids: list[int] = Form([]),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    project = project_service.create(
        db,
        owner=current_user,
        title=title,
        description=description,
        category=category,
        github_url=github_url,
        technology_ids=technology_ids,
    )

    if image and image.filename:
        image_service.attach_to_project(db, project, image)

    return deps.redirect_to_project(project.id)


@router.get("/project/{project_id}/edit")
def edit_project_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the owner can edit this project")

    return templates.TemplateResponse(request, "edit_project.html", {
        "project": project,
        "technologies": technology_service.list_all(db),
        "selected_ids": {tech.id for tech in project.technologies},
    })


@router.post("/project/{project_id}/edit")
def edit_project_submit(
    project_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    github_url: str = Form(""),
    technology_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the owner can edit this project")

    project_service.update(
        db,
        project,
        title=title,
        description=description,
        category=category,
        github_url=github_url,
        technology_ids=technology_ids,
    )
    return deps.redirect_to_project(project_id)


@router.post("/project/{project_id}/delete")
def delete_project_submit(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, "Only the owner can delete this project")
    project_service.delete(db, project)

    return deps.redirect("/home")


@router.post("/project/{project_id}/rating-submit")
def submit_rating_form(
    project_id: int,
    request: Request,
    stars: int = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    rating_service.validate_stars(stars)
    project_service.get_or_404(db, project_id)
    rating_service.upsert(db, project_id=project_id, user=current_user, stars=stars)

    return deps.redirect_to_project(project_id)


# Μόνο ο ιδιοκτήτης καταχωρεί εκδόσεις, όπως και στο API.
@router.post("/project/{project_id}/version-submit")
def submit_version_form(
    project_id: int,
    request: Request,
    version_number: str = Form(...),
    changelog: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User | None = deps.CurrentUser,
):
    if not current_user:
        return deps.redirect_to_login()

    project = project_service.get_or_404(db, project_id)
    project_service.require_owner(project, current_user, version_service.OWNER_ONLY)

    version_service.create(
        db,
        project_id=project_id,
        version_number=version_service.clean_version_number(version_number),
        changelog=changelog.strip() or None,
    )
    return deps.redirect_to_project(project_id)
