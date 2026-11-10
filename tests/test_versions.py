"""Καταχώρηση εκδόσεων από τον ιστότοπο.

Η ενότητα «Εκδόσεις» υπήρχε στη σελίδα του project, αλλά δεν υπήρχε φόρμα:
μόνο το API μπορούσε να προσθέσει έκδοση. Ο κανόνας είναι ο ίδιος και στις
δύο επιφάνειες — μόνο ο ιδιοκτήτης του project.
"""


def _submit(client, project_id, version_number="1.0.0", changelog="Πρώτη έκδοση"):
    return client.post(
        f"/project/{project_id}/version-submit",
        data={"version_number": version_number, "changelog": changelog},
        follow_redirects=False,
    )


def test_owner_can_add_version(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()

    resp = _submit(client, project_id)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/project/{project_id}/page"

    page = client.get(f"/project/{project_id}/page")
    assert "1.0.0" in page.text
    assert "Πρώτη έκδοση" in page.text
    assert "Δεν υπάρχουν καταχωρημένες εκδόσεις" not in page.text


def test_changelog_is_optional(client, make_user, make_project):
    """Χωρίς changelog η έκδοση καταχωρείται, χωρίς να μείνει κρεμασμένη παύλα."""
    make_user("owner")
    project_id = make_project()

    assert _submit(client, project_id, version_number="1.0.0", changelog="").status_code == 303

    page = client.get(f"/project/{project_id}/page")
    item = page.text.split('<div class="version-item">')[1].split("</div>")[0]
    assert "1.0.0" in item
    assert "—" not in item


def test_blank_version_number_is_rejected(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()

    assert _submit(client, project_id, version_number="   ").status_code == 422
    assert "Δεν υπάρχουν καταχωρημένες εκδόσεις" in client.get(f"/project/{project_id}/page").text


def test_non_owner_cannot_add_version(client, make_user, make_project, login):
    make_user("owner")
    project_id = make_project()

    make_user("intruder")
    assert _submit(client, project_id).status_code == 403

    login("owner")
    assert "Δεν υπάρχουν καταχωρημένες εκδόσεις" in client.get(f"/project/{project_id}/page").text


def test_anonymous_is_redirected_to_login(client, make_user, make_project):
    make_user("owner")
    project_id = make_project()
    client.cookies.clear()

    resp = _submit(client, project_id)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"


def test_form_is_shown_only_to_the_owner(client, make_user, make_project, login):
    make_user("owner")
    project_id = make_project()
    marker = f'action="/project/{project_id}/version-submit"'

    assert marker in client.get(f"/project/{project_id}/page").text

    make_user("visitor")
    assert marker not in client.get(f"/project/{project_id}/page").text

    client.cookies.clear()
    assert marker not in client.get(f"/project/{project_id}/page").text
