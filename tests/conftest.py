"""Κοινό setup για τα tests.

Οι μεταβλητές περιβάλλοντος ορίζονται *πριν* γίνει import το app, ώστε το
`database.py` να χτίσει engine πάνω σε μια απομονωμένη προσωρινή SQLite βάση
και όχι στην πραγματική PostgreSQL.
"""
import os
import tempfile

import pytest

_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH.replace("\\", "/")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from database import Base, engine  # noqa: E402


def pytest_unconfigure(config):
    """Σβήσε το προσωρινό αρχείο βάσης στο τέλος."""
    try:
        os.unlink(_TEST_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def fresh_db():
    """Κάθε test ξεκινά με άδειους πίνακες."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    """Factory: δημιουργεί χρήστη και τον συνδέει (η ενεργή session γίνεται αυτός)."""
    def _make(username="alice", password="pw123456"):
        client.post(
            "/register",
            data={"username": username, "email": f"{username}@example.com", "password": password},
        )
        resp = client.post("/login-page", data={"username": username, "password": password})
        assert resp.status_code == 200
        assert client.cookies.get("access_token")
        return username

    return _make


@pytest.fixture
def login(client):
    """Αλλαγή ενεργού χρήστη σε υπάρχοντα λογαριασμό."""
    def _login(username, password="pw123456"):
        resp = client.post("/login-page", data={"username": username, "password": password})
        assert resp.status_code == 200
        return username

    return _login


@pytest.fixture
def no_cloudinary(monkeypatch):
    """Μπλοκάρει το πραγματικό ανέβασμα στο Cloudinary."""
    monkeypatch.setattr(main, "upload_image_to_cloudinary", lambda *a, **k: "https://example.invalid/fake.png")


@pytest.fixture
def make_project(client):
    """Factory: δημιουργεί project ως ο τρέχων συνδεδεμένος χρήστης, επιστρέφει το id."""
    def _make(title="My Project", category="Web", description="desc", github_url="", technology_ids=None):
        data = {"title": title, "category": category, "description": description, "github_url": github_url}
        if technology_ids:
            data["technology_ids"] = technology_ids
        resp = client.post("/create-project", data=data, follow_redirects=False)
        assert resp.status_code == 303
        # Location: /project/{id}/page
        return int(resp.headers["location"].split("/")[2])

    return _make
