"""Η διαγραφή χρήστη δεν πρέπει να σκάει σε foreign key violation.

Δεν υπάρχει endpoint διαγραφής χρήστη σήμερα. Τα tests δουλεύουν απευθείας με
το ORM, ώστε αν προστεθεί κάποτε, το cascade να είναι ήδη σωστό.
"""
import models
from database import SessionLocal


def test_deleting_user_removes_their_comments_and_ratings(client, make_user, make_project):
    make_user("author")
    project_id = make_project(title="Project του author")

    make_user("visitor")
    client.post(
        f"/project/{project_id}/comment-submit",
        data={"content": "Ωραίο project", "category": "feature_idea"},
        follow_redirects=False,
    )
    client.post(
        f"/project/{project_id}/rating-submit",
        data={"stars": "4"},
        follow_redirects=False,
    )

    db = SessionLocal()
    try:
        assert db.query(models.Comment).count() == 1
        assert db.query(models.Rating).count() == 1

        visitor = db.query(models.User).filter(models.User.username == "visitor").one()
        db.delete(visitor)
        db.commit()

        assert db.query(models.Comment).count() == 0
        assert db.query(models.Rating).count() == 0
        # Το project ανήκει σε άλλον χρήστη και δεν πρέπει να θιγεί.
        assert db.query(models.Project).filter(models.Project.id == project_id).count() == 1
    finally:
        db.close()


def test_deleting_user_removes_their_projects(client, make_user, make_project):
    make_user("author")
    make_project(title="Θα φύγει μαζί του")

    db = SessionLocal()
    try:
        author = db.query(models.User).filter(models.User.username == "author").one()
        db.delete(author)
        db.commit()

        assert db.query(models.Project).count() == 0
    finally:
        db.close()
