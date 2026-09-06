def test_profile_page_public(client, make_user):
    make_user("pat")
    client.get("/logout")
    # ίδιο user id δεν έχει σημασία· ο πρώτος χρήστης παίρνει id 1
    resp = client.get("/user/1/page")
    assert resp.status_code == 200
    assert "pat" in resp.text


def test_profile_page_missing_user_404(client):
    assert client.get("/user/999/page").status_code == 404


def test_edit_profile_requires_login(client):
    resp = client.get("/profile/edit", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"


def test_edit_bio_persists_and_shows(client, make_user):
    make_user("quinn")
    resp = client.post("/profile/edit", data={"bio": "I build things"}, follow_redirects=False)
    assert resp.status_code == 303

    page = client.get(resp.headers["location"]).text
    assert "I build things" in page


def test_empty_bio_stored_as_none(client, make_user):
    make_user("rob")
    client.post("/profile/edit", data={"bio": "something"})
    client.post("/profile/edit", data={"bio": ""})

    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "rob").first()
        assert user.bio is None
    finally:
        db.close()
