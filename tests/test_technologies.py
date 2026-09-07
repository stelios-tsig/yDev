def test_technologies_page_requires_login(client):
    resp = client.get("/technologies-page", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"


def test_add_technology(client, make_user):
    make_user("techadder")
    resp = client.post("/technologies-page", data={"name": "Rust"}, follow_redirects=False)
    assert resp.status_code == 303
    assert "Rust" in client.get("/technologies-page").text


def test_duplicate_technology_ignored_case_insensitive(client, make_user):
    make_user("techadder")
    client.post("/technologies-page", data={"name": "Go"})
    client.post("/technologies-page", data={"name": "go"})

    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        assert db.query(models.Technology).filter(models.Technology.name.ilike("go")).count() == 1
    finally:
        db.close()


def test_blank_technology_ignored(client, make_user):
    make_user("techadder")
    client.post("/technologies-page", data={"name": "   "})

    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        assert db.query(models.Technology).count() == 0
    finally:
        db.close()
