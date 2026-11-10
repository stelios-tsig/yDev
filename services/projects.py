"""Projects: ανάκτηση, δικαιώματα, δημιουργία, ενημέρωση, διαγραφή."""
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

import models
from services import technologies as technology_service

PROJECTS_PER_PAGE = 9

# Το schemas.Project φωλιάζει owner και technologies, και το ίδιο δείχνει και
# η κάρτα στη λίστα. Χωρίς eager loading κάθε project θα ζητούσε δύο ακόμη
# queries (N+1).
_WITH_RELATIONS = (
    joinedload(models.Project.owner),
    selectinload(models.Project.technologies),
)


def get_or_404(db: Session, project_id: int, *, with_relations: bool = False) -> models.Project:
    query = db.query(models.Project)
    if with_relations:
        query = query.options(*_WITH_RELATIONS)

    project = query.filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_owner(project: models.Project, user: models.User, message: str) -> None:
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail=message)


def list_all(db: Session, *, skip: int = 0, limit: int = 100) -> list[models.Project]:
    return (
        db.query(models.Project)
        .options(*_WITH_RELATIONS)
        .offset(skip)
        .limit(limit)
        .all()
    )


def _set_technologies(db: Session, project: models.Project, technology_ids) -> None:
    project.technologies = technology_service.by_ids(db, technology_ids)


def create(
    db: Session,
    *,
    owner: models.User,
    title: str,
    description: str | None,
    category: str,
    github_url: str | None,
    technology_ids=None,
) -> models.Project:
    project = models.Project(
        title=title,
        description=description,
        category=category,
        github_url=github_url,
        owner_id=owner.id,
    )
    if technology_ids:
        _set_technologies(db, project, technology_ids)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update(
    db: Session,
    project: models.Project,
    *,
    title: str,
    description: str | None,
    category: str,
    github_url: str | None,
    technology_ids=None,
) -> models.Project:
    project.title = title
    project.description = description
    project.category = category
    project.github_url = github_url
    _set_technologies(db, project, technology_ids)

    db.commit()
    db.refresh(project)
    return project


def delete(db: Session, project: models.Project) -> None:
    db.delete(project)
    db.commit()


def owned_by(db: Session, user_id: int) -> list[models.Project]:
    return (
        db.query(models.Project)
        .filter(models.Project.owner_id == user_id)
        .order_by(models.Project.id.desc())
        .all()
    )


def search(db: Session, *, q: str = "", category: str = "", tech: int | None = None, page: int = 1):
    """Η λίστα του /home: φίλτρα, μέτρηση και σελιδοποίηση μαζί.

    Επιστρέφει (projects, page, total_pages, total) — το page επιστρέφεται
    διορθωμένο, γιατί το κόβουμε μέσα στα όρια.
    """
    query = db.query(models.Project)

    if q:
        # Η αναζήτηση καλύπτει τίτλο ΚΑΙ περιγραφή.
        like = f"%{q}%"
        query = query.filter(
            or_(models.Project.title.ilike(like), models.Project.description.ilike(like))
        )
    if category:
        query = query.filter(models.Project.category == category)
    if tech:
        query = query.filter(models.Project.technologies.any(models.Technology.id == tech))

    total = query.count()
    total_pages = max((total + PROJECTS_PER_PAGE - 1) // PROJECTS_PER_PAGE, 1)
    page = min(max(page, 1), total_pages)

    # Τα options μπαίνουν εδώ και όχι στο "query" παραπάνω, για να μην
    # επηρεάσουν το count().
    projects = (
        query.options(*_WITH_RELATIONS)
        .order_by(models.Project.id.desc())
        .offset((page - 1) * PROJECTS_PER_PAGE)
        .limit(PROJECTS_PER_PAGE)
        .all()
    )
    return projects, page, total_pages, total


def distinct_categories(db: Session) -> list[str]:
    rows = db.query(models.Project.category).distinct().order_by(models.Project.category).all()
    return [row[0] for row in rows if row[0]]
