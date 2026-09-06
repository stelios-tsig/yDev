def test_create_and_view_project(client, make_user, make_project):
    make_user("owner")
    pid = make_project(title="Cool App", category="Web")

    resp = client.get(f"/project/{pid}/page")
    assert resp.status_code == 200
    assert "Cool App" in resp.text
    assert "owner" in resp.text


def test_owner_can_edit_project(client, make_user, make_project):
    make_user("owner")
    pid = make_project(title="Before", category="Web")

    resp = client.post(
        f"/project/{pid}/edit",
        data={"title": "After", "category": "CLI", "description": "new", "github_url": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303

    page = client.get(f"/project/{pid}/page").text
    assert "After" in page
    assert "Before" not in page


def test_non_owner_cannot_open_edit_page(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    make_user("intruder")  # switches active session

    resp = client.get(f"/project/{pid}/edit")
    assert resp.status_code == 403


def test_non_owner_cannot_submit_edit(client, make_user, make_project):
    make_user("owner")
    pid = make_project(title="Original")
    make_user("intruder")

    resp = client.post(
        f"/project/{pid}/edit",
        data={"title": "Hacked", "category": "Web", "description": "", "github_url": ""},
    )
    assert resp.status_code == 403
    # login back as owner to read the page
    client.post("/login-page", data={"username": "owner", "password": "pw123456"})
    assert "Hacked" not in client.get(f"/project/{pid}/page").text


def test_owner_can_delete_project(client, make_user, make_project):
    make_user("owner")
    pid = make_project()

    resp = client.post(f"/project/{pid}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/home"
    assert client.get(f"/project/{pid}/page").status_code == 404


def test_non_owner_cannot_delete_project(client, make_user, make_project):
    make_user("owner")
    pid = make_project()
    make_user("intruder")

    resp = client.post(f"/project/{pid}/delete")
    assert resp.status_code == 403


def test_image_upload_rejects_oversized_file(client, make_user, no_cloudinary):
    make_user("owner")
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (6 * 1024 * 1024)
    resp = client.post(
        "/create-project",
        data={"title": "WithBigImage", "category": "Web", "description": "", "github_url": ""},
        files={"image": ("big.png", big, "image/png")},
    )
    assert resp.status_code == 400
    assert "5MB" in resp.text


def test_image_upload_accepts_small_file(client, make_user, no_cloudinary):
    make_user("owner")
    small = b"\x89PNG\r\n\x1a\n" + b"0" * 512
    resp = client.post(
        "/create-project",
        data={"title": "WithSmallImage", "category": "Web", "description": "", "github_url": ""},
        files={"image": ("small.png", small, "image/png")},
        follow_redirects=False,
    )
    assert resp.status_code == 303
