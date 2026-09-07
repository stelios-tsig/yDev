def test_root_redirects_to_home(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/home"


def test_root_follows_to_home(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "yDev" in resp.text
