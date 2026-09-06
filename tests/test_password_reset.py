from datetime import datetime, timedelta, timezone

import pytest

import main


@pytest.fixture
def captured_emails(monkeypatch):
    sent = []
    monkeypatch.setattr(main, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def _latest_token():
    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        return db.query(models.PasswordResetToken).order_by(models.PasswordResetToken.id.desc()).first()
    finally:
        db.close()


def _token_count():
    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        return db.query(models.PasswordResetToken).count()
    finally:
        db.close()


def test_forgot_password_page_renders(client):
    resp = client.get("/forgot-password")
    assert resp.status_code == 200
    assert "Επαναφορά κωδικού" in resp.text


def test_unknown_email_no_token_generic_message(client, captured_emails):
    resp = client.post("/forgot-password", data={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "Αν υπάρχει λογαριασμός" in resp.text
    assert _token_count() == 0
    assert captured_emails == []


def test_known_email_creates_token_and_sends_link(client, make_user, captured_emails):
    make_user("frank")
    client.get("/logout")

    resp = client.post("/forgot-password", data={"email": "frank@example.com"})
    assert resp.status_code == 200
    assert "Αν υπάρχει λογαριασμός" in resp.text

    token = _latest_token()
    assert token is not None and token.used is False
    assert len(captured_emails) == 1
    to, _subject, body = captured_emails[0]
    assert to == "frank@example.com"
    assert f"/reset-password/{token.token}" in body


def test_reset_page_valid_token_shows_form(client, make_user, captured_emails):
    make_user("gina")
    client.post("/forgot-password", data={"email": "gina@example.com"})
    token = _latest_token().token

    resp = client.get(f"/reset-password/{token}")
    assert resp.status_code == 200
    assert 'action="/reset-password/' in resp.text
    assert "δεν είναι έγκυρος" not in resp.text


def test_reset_page_bad_token_shows_error(client):
    resp = client.get("/reset-password/not-a-real-token")
    assert resp.status_code == 200
    assert "δεν είναι έγκυρος ή έχει λήξει" in resp.text


def test_reset_changes_password_and_consumes_token(client, make_user, captured_emails):
    make_user("hank")
    client.post("/forgot-password", data={"email": "hank@example.com"})
    token = _latest_token().token
    client.get("/logout")

    resp = client.post(f"/reset-password/{token}", data={"password": "brandnew1"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login-page"

    # old password no longer works
    bad = client.post("/login-page", data={"username": "hank", "password": "pw123456"})
    assert not bad.cookies.get("access_token")
    # new password works
    good = client.post("/login-page", data={"username": "hank", "password": "brandnew1"}, follow_redirects=False)
    assert good.status_code == 303

    assert _latest_token().used is True


def test_used_token_cannot_be_reused(client, make_user, captured_emails):
    make_user("ivy")
    client.post("/forgot-password", data={"email": "ivy@example.com"})
    token = _latest_token().token

    client.post(f"/reset-password/{token}", data={"password": "firstchange"})
    resp = client.post(f"/reset-password/{token}", data={"password": "secondchange"})
    assert resp.status_code == 200
    assert "δεν είναι έγκυρος ή έχει λήξει" in resp.text


def test_expired_token_rejected(client, make_user):
    make_user("jane")

    from database import SessionLocal
    import models

    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == "jane").first()
        db.add(models.PasswordResetToken(
            token="expired-token-123",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        ))
        db.commit()
    finally:
        db.close()

    resp = client.get("/reset-password/expired-token-123")
    assert "δεν είναι έγκυρος ή έχει λήξει" in resp.text

    resp = client.post("/reset-password/expired-token-123", data={"password": "whatever1"})
    assert "δεν είναι έγκυρος ή έχει λήξει" in resp.text


def test_short_password_rejected(client, make_user, captured_emails):
    make_user("kyle")
    client.post("/forgot-password", data={"email": "kyle@example.com"})
    token = _latest_token().token

    resp = client.post(f"/reset-password/{token}", data={"password": "abc"})
    assert resp.status_code == 200
    assert "τουλάχιστον 6 χαρακτήρες" in resp.text
    assert _latest_token().used is False


def test_login_page_has_forgot_link(client):
    assert 'href="/forgot-password"' in client.get("/login-page").text
