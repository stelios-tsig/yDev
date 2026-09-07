def test_register_redirects_to_login(client):
    resp = client.post(
        "/register",
        data={"username": "bob", "email": "bob@example.com", "password": "pw123456"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"


def test_register_duplicate_email_rejected(client):
    payload = {"username": "u1", "email": "dup@example.com", "password": "pw123456"}
    client.post("/register", data=payload)
    payload["username"] = "u2"
    resp = client.post("/register", data=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.text.lower()


def test_login_sets_cookie_and_redirects_home(client):
    client.post("/register", data={"username": "carol", "email": "carol@example.com", "password": "pw123456"})
    resp = client.post(
        "/login-page",
        data={"username": "carol", "password": "pw123456"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/home"
    assert resp.cookies.get("access_token")


def test_login_wrong_password_shows_error(client):
    client.post("/register", data={"username": "dave", "email": "dave@example.com", "password": "pw123456"})
    resp = client.post("/login-page", data={"username": "dave", "password": "wrong"})
    assert resp.status_code == 200
    assert "Λάθος όνομα χρήστη ή κωδικός" in resp.text
    assert not resp.cookies.get("access_token")


def test_logout_clears_cookie(client, make_user):
    make_user("erin")
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert client.cookies.get("access_token") is None


def test_create_project_page_requires_login(client):
    resp = client.get("/create-project", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"


def test_register_normalises_email_case(client):
    client.post(
        "/register",
        data={"username": "mixed", "email": "  MiXeD@Example.COM ", "password": "pw123456"},
    )
    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "mixed").first()
        assert user.email == "mixed@example.com"
    finally:
        db.close()


def test_duplicate_email_check_is_case_insensitive(client):
    client.post("/register", data={"username": "a1", "email": "dup2@example.com", "password": "pw123456"})
    resp = client.post("/register", data={"username": "a2", "email": "DUP2@EXAMPLE.COM", "password": "pw123456"})
    assert resp.status_code == 400


def test_json_create_user_hashes_password(client):
    resp = client.post(
        "/users/",
        json={"username": "jsonuser", "email": "jsonuser@example.com", "password": "pw123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "jsonuser"
    assert "password" not in body
    assert "hashed_password" not in body
