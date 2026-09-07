"""Αποστολή email.

Χωρίς ρύθμιση SMTP, το μήνυμα απλώς τυπώνεται στο console (dev mode) — χρήσιμο
για development και για τα tests. Αν οριστούν οι μεταβλητές SMTP_* στο .env,
το email φεύγει κανονικά μέσω smtplib.
"""
import os
import smtplib
import sys
import traceback
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def _print_to_console(to: str, subject: str, body: str) -> None:
    print("=" * 60, file=sys.stderr)
    print(f"[email] To:      {to}", file=sys.stderr)
    print(f"[email] Subject: {subject}", file=sys.stderr)
    print(body, file=sys.stderr)
    print("=" * 60, file=sys.stderr)


def send_email(to: str, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")

    if not host:
        #Dev mode: το γράφουμε στο console αντί να το στείλουμε.
        _print_to_console(to, subject, body)
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or user or "no-reply@ydev.local"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    except Exception:
        #Δεν ρίχνουμε το request· γράφουμε το σφάλμα και τυπώνουμε το μήνυμα
        #στην κονσόλα ώστε να μη χαθεί ο σύνδεσμος επαναφοράς.
        print("[email] SMTP αποτυχία — το μήνυμα δεν στάλθηκε:", file=sys.stderr)
        traceback.print_exc()
        _print_to_console(to, subject, body)
