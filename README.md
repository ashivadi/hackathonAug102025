# DoneGlow - MyLifeOS Personal Assistant

DoneGlow powered by Claude plans your day at 7:00 AM, renders an Eisenhower Matrix, schedules, provides the top Three Needle movers, AM/PM affirmations, Stress helper Guide, and supports inbox invites + trade-off decisions. SQLite by default. Anthropic integration.

## Quick Start (with uv)
```bash
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env  # update google client id and client secret for google calendar integration 
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Debugging
```
find app -name '__pycache__' -type d -exec rm -rf {} +
uvicorn app.main:app --reload
```
