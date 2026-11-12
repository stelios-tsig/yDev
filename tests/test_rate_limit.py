import pytest

import rate_limit


@pytest.fixture
def rate_limiting_on(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    rate_limit.clear_all()
    yield
    rate_limit.clear_all()


def _forgot(client, email="x@example.com", headers=None):
    return client.post("/forgot-password", data={"email": email}, headers=headers or {})


def test_forgot_password_is_rate_limited(client, rate_limiting_on):
    # 5 per minute allowed on /forgot-password
    for _ in range(5):
        assert _forgot(client).status_code == 200
    assert _forgot(client).status_code == 429


def test_disabled_by_default_in_tests(client):
    # conftest sets RATE_LIMIT_ENABLED=false, so hammering stays 200
    for _ in range(15):
        assert _forgot(client, "y@example.com").status_code == 200


def test_spoofed_forwarded_for_cannot_reset_the_counter(client, rate_limiting_on, monkeypatch):
    """Χωρίς trusted proxy, το X-Forwarded-For του πελάτη αγνοείται.

    Αλλιώς οποιοσδήποτε στέλνει τυχαία IP σε κάθε αίτημα και παίρνει κάθε
    φορά καθαρό μετρητή — δηλαδή παρακάμπτει τελείως το rate limiting.
    """
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)

    for i in range(5):
        resp = _forgot(client, headers={"X-Forwarded-For": f"10.0.0.{i}"})
        assert resp.status_code == 200

    blocked = _forgot(client, headers={"X-Forwarded-For": "10.0.0.99"})
    assert blocked.status_code == 429


def test_trusted_proxy_uses_the_address_it_appended(client, rate_limiting_on, monkeypatch):
    """Με ένα trusted proxy μετράει η τελευταία τιμή, όχι η πρώτη.

    Ο πελάτης ελέγχει την αρχή του header· το proxy μας προσθέτει στο τέλος.
    """
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "1")

    # Ίδια πραγματική IP (η τελευταία), διαφορετικό spoofed πρόθεμα.
    for i in range(5):
        resp = _forgot(client, headers={"X-Forwarded-For": f"1.2.3.{i}, 203.0.113.7"})
        assert resp.status_code == 200

    assert _forgot(client, headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7"}).status_code == 429

    # Άλλη πραγματική IP -> δικός της μετρητής.
    assert _forgot(client, headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.8"}).status_code == 200


def test_stale_keys_are_swept(monkeypatch):
    """Τα κλειδιά δεν μένουν για πάντα στη μνήμη.

    Χωρίς τον καθαρισμό, κάθε IP που εμφανίστηκε έστω μία φορά θα έμενε στη
    μνήμη της διεργασίας μέχρι το επόμενο restart.
    """
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
    rate_limit.clear_all()

    class _FakeRequest:
        def __init__(self, host):
            self.headers = {}
            self.client = type("C", (), {"host": host})()

    for i in range(50):
        rate_limit.rate_limit(_FakeRequest(f"10.1.0.{i}"), "login", max_calls=10, window_seconds=60)

    assert rate_limit._key_count() == 50

    # Γερνάμε τα timestamps πέρα από το παράθυρό τους και ζητάμε νέα σάρωση,
    # αντί να πειράξουμε το ρολόι όλης της διεργασίας.
    for timestamps, window in rate_limit._hits.values():
        for _ in range(len(timestamps)):
            timestamps.append(timestamps.popleft() - window - 1)

    # _NEVER_SWEPT και όχι 0.0: το time.monotonic() μετράει από το boot, οπότε
    # σε φρέσκο CI runner (uptime < _SWEEP_INTERVAL) το 0.0 ΔΕΝ θα ενεργοποιούσε
    # σάρωση και το test θα έπεφτε ανάλογα με το πόση ώρα είναι ανοιχτό το μηχάνημα.
    rate_limit._last_sweep = rate_limit._NEVER_SWEPT

    rate_limit.rate_limit(_FakeRequest("10.2.0.1"), "login", max_calls=10, window_seconds=60)

    # Έμεινε μόνο το κλειδί που μόλις δημιουργήθηκε.
    assert rate_limit._key_count() == 1

    rate_limit.clear_all()
