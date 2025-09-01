"""Gmail helpers for QuiverQuant ingestion."""
from __future__ import annotations
import os, json
from datetime import datetime
from typing import List, Dict, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", os.path.join("config", "gmail_token.json"))
CREDS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", os.path.join("config", "gmail_credentials.json"))


def get_service():
    """Return an authenticated Gmail service instance.

    Credentials are stored under ``./config`` and reused on subsequent runs.
    """
    creds: Optional[Credentials] = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                raise FileNotFoundError(f"gmail_credentials_missing:{CREDS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service


def _get_label_id(service, label_name: str) -> Optional[str]:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl.get("name") == label_name:
            return lbl.get("id")
    return None


def search_messages(service, query: str, label: str) -> List[str]:
    """Return a list of message ids matching the query and label."""
    label_id = _get_label_id(service, label)
    results: List[str] = []
    req = service.users().messages().list(userId="me", q=query, labelIds=[label_id] if label_id else None)
    while req is not None:
        resp = req.execute()
        msgs = resp.get("messages", [])
        results.extend(m.get("id") for m in msgs)
        req = service.users().messages().list_next(req, resp)
    results.reverse()  # Gmail API returns oldest first
    return list(reversed(results))  # newest first


def fetch_message_html(service, message_id: str) -> Dict[str, Optional[str]]:
    """Fetch a single Gmail message and return relevant fields."""
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    parts = payload.get("parts", [])
    html_part = None
    for part in parts:
        if part.get("mimeType") == "text/html":
            html_part = part.get("body", {}).get("data")
            break
    if html_part:
        import base64, codecs
        decoded = base64.urlsafe_b64decode(html_part.encode("utf-8"))
        html = codecs.decode(decoded, "utf-8")
    else:
        html = ""
    return {
        "message_id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "subject": headers.get("subject"),
        "from": headers.get("from"),
        "received_at": datetime.fromtimestamp(int(msg.get("internalDate", "0")) / 1000.0),
        "snippet": msg.get("snippet"),
        "html": html,
    }
