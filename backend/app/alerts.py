"""Utility functions for sending optional alerts."""

import os
import smtplib
from email.message import EmailMessage


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send an email using SMTP credentials from environment variables."""
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    if not host or not to_address:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user or "macmarket@example.com"
    msg["To"] = to_address
    msg.set_content(body)
    try:  # pragma: no cover - external call
        with smtplib.SMTP(host) as server:
            if user:
                server.starttls()
                server.login(user, password or "")
            server.send_message(msg)
        return True
    except Exception:
        return False


def send_sms(number: str, body: str) -> bool:
    """Placeholder SMS sender. Requires environment variables if using Twilio."""
    sid = os.getenv("TWILIO_SID")
    token = os.getenv("TWILIO_TOKEN")
    from_num = os.getenv("TWILIO_FROM")
    if not all([sid, token, from_num, number]):
        return False
    try:  # pragma: no cover - external call
        from twilio.rest import Client

        Client(sid, token).messages.create(to=number, from_=from_num, body=body)
        return True
    except Exception:
        return False
