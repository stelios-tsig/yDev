"""Αποστολή email.

Σειρά προτεραιότητας:
  1. Resend HTTP API  — αν υπάρχει RESEND_API_KEY (δουλεύει σε hosts που
     μπλοκάρουν SMTP, π.χ. Render).
  2. SMTP             — αν υπάρχει SMTP_HOST (π.χ. Gmail, για τοπική χρήση).
  3. Console          — αλλιώς τυπώνεται στο stderr (dev / tests).

Αν το επιλεγμένο κανάλι αποτύχει, το μήνυμα τυπώνεται στο console ώστε να
μη χαθεί ο σύνδεσμος επαναφοράς και να μη ρίξει το request.
"""
import json
import os
import smtplib
import sys
import traceback
import urllib.request
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def _print_to_console(to: str, subject: str, body: str) -> None:
    print("=" * 60, file=sys.stderr)
    print(f"[email] To:      {to}", file=sys.stderr)
    print(f"[email] Subject: {subject}", file=sys.stderr)
    print(body, file=sys.stderr)
    print("=" * 60, file=sys.stderr)


def _send_via_resend(to: str, subject: str, body: str) -> None:
    payload = json.dumps({
        "from": os.getenv("EMAIL_FROM") or "onboarding@resend.dev",
        "to": [to],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def _send_via_smtp(to: str, subject: str, body: str) -> None:
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM") or user or "no-reply@ydev.local"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587")), timeout=20) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_email(to: str, subject: str, body: str) -> None:
    try:
        if os.getenv("RESEND_API_KEY"):
            _send_via_resend(to, subject, body)
            return
        if os.getenv("SMTP_HOST"):
            _send_via_smtp(to, subject, body)
            return
    except Exception:
        print("[email] αποτυχία αποστολής — το μήνυμα δεν στάλθηκε:", file=sys.stderr)
        traceback.print_exc()

    _print_to_console(to, subject, body)
