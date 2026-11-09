"""Τα ανοιχτά endpoints δεν πρέπει να εκθέτουν τα email των χρηστών.

Τα /projects/, /projects/{id}/comments/ και /projects/{id}/ratings/ διαβάζονται
χωρίς σύνδεση. Αν φώλιαζαν το schemas.User, το email κάθε χρήστη που έχει
ανεβάσει project ή γράψει σχόλιο θα ήταν δημόσιο.
"""


def test_projects_list_hides_owner_email(client, make_user, make_project):
    make_user("owner")
    make_project(title="Public Project")
    client.cookies.clear()

    resp = client.get("/projects/")
    assert resp.status_code == 200

    owner = resp.json()[0]["owner"]
    assert owner["username"] == "owner"
    assert "email" not in owner


def test_project_detail_hides_owner_email(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()
    client.cookies.clear()

    resp = client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    assert "email" not in resp.json()["owner"]


def test_comments_hide_author_email(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()
    client.post(
        f"/project/{project_id}/comment-submit",
        data={"content": "Ωραίο project", "category": "feature_idea"},
        follow_redirects=False,
    )
    client.cookies.clear()

    resp = client.get(f"/projects/{project_id}/comments/")
    assert resp.status_code == 200

    author = resp.json()[0]["user"]
    assert author["username"] == "owner"
    assert "email" not in author


def test_ratings_hide_voter_email(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()
    client.post(
        f"/project/{project_id}/rating-submit",
        data={"stars": "4"},
        follow_redirects=False,
    )
    client.cookies.clear()

    resp = client.get(f"/projects/{project_id}/ratings/")
    assert resp.status_code == 200

    voter = resp.json()[0]["user"]
    assert voter["username"] == "owner"
    assert "email" not in voter


def test_user_creation_still_returns_own_email(client):
    """Το POST /users/ επιστρέφει τον ίδιο τον λογαριασμό — εκεί το email μένει."""
    resp = client.post(
        "/users/",
        json={"username": "apiuser", "email": "apiuser@example.com", "password": "pw123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "apiuser@example.com"
