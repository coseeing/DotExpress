# DotExpress Client Init Server

This folder contains a temporary FastAPI + SQLAlchemy server for the DotExpress client initialization endpoint.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r server/requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The default SQLite database path is:

```text
server/data/dotexpress.sqlite3
```

## Endpoint

```http
POST /client/init
```

The first iteration only records client initialization data and returns version metadata. It does not expose statistics, reporting, or admin query endpoints.
