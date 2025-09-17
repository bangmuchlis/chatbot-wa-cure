import os
import sys
import logging
import pickle
import base64
import json
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict

# MCP
from mcp.server.fastmcp import FastMCP

# Google libs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Email libs
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

mcp = FastMCP("Scheduler_Server")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
TOKEN_FILE = "src/token.pickle"
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

# Temporary memory
PENDING_EVENTS: Dict[str, Dict[str, Any]] = {}
_last_event: dict | None = None  # simpan event terakhir

# Google API Scopes
SCOPES = {
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
    ],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
}


# ---------------------------
# Google authentication
# ---------------------------
def get_credentials(required_scopes: List[str]) -> Credentials:
    creds: Optional[Credentials] = None

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)
        except Exception as e:
            log.warning("Failed loading token.pickle: %s", e)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                log.info("Google credentials refreshed.")
            except Exception as e:
                log.warning("Failed to refresh credentials: %s", e)
                creds = None
        else:
            if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
                raise FileNotFoundError(
                    f"Google credentials not found: {GOOGLE_APPLICATION_CREDENTIALS}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_APPLICATION_CREDENTIALS, required_scopes
            )
            creds = flow.run_local_server(port=0)

        try:
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
            log.info("Saved new token to %s", TOKEN_FILE)
        except Exception as e:
            log.warning("Could not save token.pickle: %s", e)

    return creds


def get_gcal_service():
    creds = get_credentials(SCOPES["calendar"])
    return build("calendar", "v3", credentials=creds)


def get_gmail_service():
    creds = get_credentials(SCOPES["gmail"])
    return build("gmail", "v1", credentials=creds)


# ---------------------------
# Tools
# ---------------------------
@mcp.tool()
def get_current_datetime() -> dict:
    """Return UTC and Asia/Jakarta datetime for convenience."""
    try:
        now_utc = datetime.utcnow().isoformat() + "Z"
        now_local = (datetime.utcnow() + timedelta(hours=7)).isoformat()
        return {"utc": now_utc, "asia_jakarta": now_local}
    except Exception as e:
        log.error("get_current_datetime error: %s", e, exc_info=True)
        return {"error": str(e)}


@mcp.tool()
def create_calendar_event(title: str, start_time: str, end_time: str, attendees: list[str] | None = None) -> dict:
    """Create Google Calendar event and auto-send invitations."""
    global _last_event
    try:
        service = get_gcal_service()

        event = {
            "summary": title,
            "start": {"dateTime": start_time, "timeZone": "Asia/Jakarta"},
            "end": {"dateTime": end_time, "timeZone": "Asia/Jakarta"},
        }

        if attendees:
            event["attendees"] = [{"email": a} for a in attendees]

        # Add Google Meet link
        event["conferenceData"] = {
            "createRequest": {
                "requestId": f"meet-{int(datetime.utcnow().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

        created_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",  # kirim otomatis ke attendees
            )
            .execute()
        )

        _last_event = created_event  # simpan untuk fallback email

        meeting_link = created_event.get("hangoutLink")
        event_link = created_event.get("htmlLink")

        log.info("Created event %s (meet: %s)", created_event.get("id"), meeting_link)

        return {
            "success": True,
            "event_id": created_event.get("id"),
            "event_link": event_link,
            "meeting_link": meeting_link,
            "attendees": attendees or [],
        }

    except Exception as e:
        log.error("create_calendar_event error: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


def _create_message(sender: str, to: str, subject: str, body: str, is_html: bool) -> str:
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if is_html else "plain"))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

@mcp.tool()
def delete_calendar_event(event_id: str) -> dict:
    """
    Delete a Google Calendar event.
    User must provide event_id.
    """
    try:
        if not event_id:
            return {"success": False, "error": "Event ID is required for deletion."}

        service = get_gcal_service()
        service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()

        log.info("Deleted event %s", event_id)
        return {"success": True, "deleted_event_id": event_id}

    except Exception as e:
        log.error("delete_calendar_event error: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


@mcp.tool()
def send_email(to: list[str] | str | None, subject: str, body: str, is_html: bool = True) -> dict:
    """Send email via Gmail API. If no recipient, fallback to last event attendees."""
    global _last_event
    try:
        recipients: list[str] = []

        if to:
            recipients = [to] if isinstance(to, str) else to
        elif _last_event and "attendees" in _last_event:
            recipients = [a["email"] for a in _last_event.get("attendees", [])]
            log.info("Fallback: sending to last event attendees: %s", recipients)

        if not recipients:
            return {"success": False, "error": "Missing recipient emails"}

        service = get_gmail_service()

        # Fallback sender
        sender = MAIL_DEFAULT_SENDER
        if not sender:
            profile = service.users().getProfile(userId="me").execute()
            sender = profile.get("emailAddress")

        for recipient in recipients:
            raw_message = _create_message(sender, recipient, subject, body, is_html)
            sent = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            log.info("Email sent to %s with id %s", recipient, sent.get("id"))

        return {"success": True, "sent_to": recipients}

    except Exception as e:
        log.error("send_email error: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


# ---------------------------
# Run MCP server
# ---------------------------
if __name__ == "__main__":
    log.info("🚀 Starting Scheduler MCP Server (STDIO transport)...")
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        log.info("🛑 Server stopped by user.")
        sys.exit(0)
    except Exception:
        log.exception("Fatal error in scheduler_server")
        sys.exit(1)
