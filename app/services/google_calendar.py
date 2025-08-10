import os

# Allow HTTP for local development only. Remove/guard this for production!
if os.getenv("OAUTHLIB_INSECURE_TRANSPORT") is None:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from datetime import datetime, timedelta
from typing import Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from app.models.calendar_account import CalendarAccount
from app.models.event import Event
from app.models.user import User
from sqlalchemy.orm import Session
from dateutil import parser as dateparse

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config():
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "project_id": "personal-assistant",
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uris": [
                os.getenv(
                    "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback"
                )
            ],
            "javascript_origins": ["http://127.0.0.1:8000"],
        }
    }


def start_oauth(state: str) -> str:
    scopes = os.getenv(
        "GOOGLE_SCOPES", "https://www.googleapis.com/auth/calendar"
    ).split()
    flow = Flow.from_client_config(
        _client_config(), scopes=scopes, redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
    )
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def finish_oauth(db: Session, user: User, full_callback_url: str) -> CalendarAccount:
    scopes = os.getenv(
        "GOOGLE_SCOPES", "https://www.googleapis.com/auth/calendar"
    ).split()
    flow = Flow.from_client_config(
        _client_config(), scopes=scopes, redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
    )
    flow.fetch_token(authorization_response=full_callback_url)
    creds = flow.credentials

    acct = (
        db.query(CalendarAccount)
        .filter_by(user_id=user.id, provider="google")
        .one_or_none()
    )
    if not acct:
        acct = CalendarAccount(user_id=user.id, provider="google")
        db.add(acct)

    acct.access_token = creds.token
    acct.refresh_token = getattr(creds, "refresh_token", acct.refresh_token)
    acct.token_uri = creds.token_uri
    acct.client_id = creds.client_id
    acct.client_secret = creds.client_secret
    acct.scope = " ".join(creds.scopes or [])
    acct.token_expiry = creds.expiry
    db.commit()
    db.refresh(acct)
    return acct


def _build_creds(acct: CalendarAccount) -> Credentials:
    creds = Credentials(
        token=acct.access_token,
        refresh_token=acct.refresh_token,
        token_uri=acct.token_uri or GOOGLE_TOKEN_URI,
        client_id=acct.client_id,
        client_secret=acct.client_secret,
        scopes=(acct.scope or "").split(),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _service(acct: CalendarAccount):
    creds = _build_creds(acct)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _iso_to_dt(s: str):
    if not s:
        return None
    return dateparse.parse(s)


def sync_primary(db: Session, user: User, days_forward: int = 14) -> int:
    acct = (
        db.query(CalendarAccount)
        .filter_by(user_id=user.id, provider="google")
        .one_or_none()
    )
    if not acct:
        raise RuntimeError("No connected Google Calendar account")
    svc = _service(acct)

    now = datetime.utcnow().isoformat() + "Z"
    time_max = (datetime.utcnow() + timedelta(days=days_forward)).isoformat() + "Z"
    events_result = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=now,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = events_result.get("items", [])
    count = 0
    for it in items:
        eid = it["id"]
        start = _iso_to_dt(
            it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
        )
        end = _iso_to_dt(
            it.get("end", {}).get("dateTime") or it.get("end", {}).get("date")
        )
        ev = (
            db.query(Event)
            .filter_by(user_id=user.id, provider="google", external_id=eid)
            .one_or_none()
        )
        if not ev:
            ev = Event(
                user_id=user.id,
                provider="google",
                external_id=eid,
                summary=it.get("summary"),
                location=it.get("location"),
                start=start,
                end=end,
                status=it.get("status"),
                raw=it,
            )
            db.add(ev)
        else:
            ev.summary = it.get("summary")
            ev.location = it.get("location")
            ev.start = start
            ev.end = end
            ev.status = it.get("status")
            ev.raw = it
        count += 1
    db.commit()
    return count


def create_event(
    db: Session,
    user: User,
    summary: str,
    start_iso: str,
    end_iso: str,
    location: str | None = None,
) -> Event:
    acct = (
        db.query(CalendarAccount)
        .filter_by(user_id=user.id, provider="google")
        .one_or_none()
    )
    if not acct:
        raise RuntimeError("No connected Google Calendar account")
    svc = _service(acct)
    body = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if location:
        body["location"] = location
    resp = svc.events().insert(calendarId="primary", body=body).execute()
    ev = Event(
        user_id=user.id,
        provider="google",
        external_id=resp["id"],
        summary=resp.get("summary"),
        location=resp.get("location"),
        start=_iso_to_dt(resp["start"].get("dateTime") or resp["start"].get("date")),
        end=_iso_to_dt(resp["end"].get("dateTime") or resp["end"].get("date")),
        status=resp.get("status"),
        raw=resp,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def update_event(db: Session, user: User, external_id: str, patch: Dict) -> Event:
    acct = (
        db.query(CalendarAccount)
        .filter_by(user_id=user.id, provider="google")
        .one_or_none()
    )
    if not acct:
        raise RuntimeError("No connected Google Calendar account")
    svc = _service(acct)
    resp = (
        svc.events()
        .patch(calendarId="primary", eventId=external_id, body=patch)
        .execute()
    )
    ev = (
        db.query(Event)
        .filter_by(user_id=user.id, provider="google", external_id=external_id)
        .one_or_none()
    )
    if not ev:
        ev = Event(user_id=user.id, provider="google", external_id=resp["id"])
        db.add(ev)
    ev.summary = resp.get("summary")
    ev.location = resp.get("location")
    ev.start = _iso_to_dt(resp["start"].get("dateTime") or resp["start"].get("date"))
    ev.end = _iso_to_dt(resp["end"].get("dateTime") or resp["end"].get("date"))
    ev.status = resp.get("status")
    ev.raw = resp
    db.commit()
    db.refresh(ev)
    return ev
