def test_root_redirects_to_home(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/home"


def test_root_follows_to_home(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "yDev" in resp.text


def test_unknown_url_html_404_page(client):
    resp = client.get("/no/such/page", headers={"accept": "text/html"})
    assert resp.status_code == 404
    assert "404" in resp.text
    assert "Πίσω στην αρχική" in resp.text


def test_unknown_url_json_404_for_api_clients(client):
    resp = client.get("/no/such/page", headers={"accept": "application/json"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not Found"
