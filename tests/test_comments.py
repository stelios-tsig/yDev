import pytest


def _add_comment(client, pid, content="Nice work", category="feature_idea"):
    return client.post(
        f"/project/{pid}/comment-submit",
        data={"content": content, "category": category},
        follow_redirects=False,
    )


def test_add_comment_appears_on_page(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    make_user("commenter")

    resp = _add_comment(client, pid, content="Love this")
    assert resp.status_code == 303
    assert "Love this" in client.get(f"/project/{pid}/page").text


def test_comment_invalid_category_rejected(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    resp = _add_comment(client, pid, category="not_a_category")
    assert resp.status_code == 422


def test_author_can_edit_own_comment(client, make_user, make_project, db_comment_id):
    cid, pid = db_comment_id
    resp = client.post(
        f"/comment/{cid}/edit",
        data={"content": "edited text", "category": "bug_report"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    page = client.get(f"/project/{pid}/page").text
    assert "edited text" in page


def test_non_author_cannot_edit_comment(client, make_user, make_project, db_comment_id):
    cid, _ = db_comment_id
    make_user("someone_else")
    resp = client.get(f"/comment/{cid}/edit")
    assert resp.status_code == 403


def test_project_owner_can_delete_others_comment(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    make_user("commenter")
    _add_comment(client, pid, content="to be removed")
    # back to owner
    client.post("/login-page", data={"username": "owner", "password": "pw123456"})

    cid = _latest_comment_id()
    resp = client.post(f"/comment/{cid}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert "to be removed" not in client.get(f"/project/{pid}/page").text


def test_unrelated_user_cannot_delete_comment(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    make_user("commenter")
    _add_comment(client, pid)
    cid = _latest_comment_id()
    make_user("stranger")

    resp = client.post(f"/comment/{cid}/delete")
    assert resp.status_code == 403


# --- helpers that read straight from the DB -------------------------------

def _latest_comment_id():
    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        return db.query(models.Comment).order_by(models.Comment.id.desc()).first().id
    finally:
        db.close()


@pytest.fixture
def db_comment_id(client, make_user, make_project):
    """owner δημιουργεί project, commenter αφήνει ένα σχόλιο· επιστρέφει (comment_id, project_id)."""
    make_user("owner")
    pid = make_project()
    make_user("commenter")
    _add_comment(client, pid, content="original text")
    return _latest_comment_id(), pid
