import pytest

import rate_limit


@pytest.fixture
def rate_limiting_on(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    rate_limit.clear_all()
    yield
    rate_limit.clear_all()


def test_forgot_password_is_rate_limited(client, rate_limiting_on):
    # 5 per minute allowed on /forgot-password
    for _ in range(5):
        r = client.post("/forgot-password", data={"email": "x@example.com"})
        assert r.status_code == 200
    r = client.post("/forgot-password", data={"email": "x@example.com"})
    assert r.status_code == 429


def test_disabled_by_default_in_tests(client):
    # conftest sets RATE_LIMIT_ENABLED=false, so hammering stays 200
    for _ in range(15):
        r = client.post("/forgot-password", data={"email": "y@example.com"})
        assert r.status_code == 200
