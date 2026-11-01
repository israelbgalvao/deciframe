# AGENTS.md

deciframe is a song-discovery tool for musicians: search by title/artist,
genre, chords you already know, or a famous chord sequence, and it finds
similar songs. Full description: [README.md](README.md).

## Stack

- Backend: Python 3.9, Flask 3.1, gunicorn. `main.py` loads
  `data/top/dataset_final.csv` into memory once at startup. The sequence
  catalog lives in SQLite via `sequencias_db.py`; its path comes from
  `SEQUENCIAS_DB_PATH` (default `db/sequencias.db`), and `db/` is ignored by
  Git and Docker.
- Frontend: AngularJS 1.4.9 + jQuery, loaded from CDN in `static/index.html`,
  no build step. Legacy, and there's no plan to modernize the stack itself —
  but touching it is no longer off-limits when a task needs it; see
  [docs/adr/0003-lift-frontend-freeze.md](docs/adr/0003-lift-frontend-freeze.md).
- Deploy: local-only via Docker for now. No cloud target has been chosen.

## Run locally

Docker (matches how the app actually ships):

```
docker build -t ciframe .
docker run -p 8080:8080 -v ciframe-db:/app/db ciframe
```

The named volume `ciframe-db` keeps the sequence catalog across container
recreation.

Or a plain virtualenv:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py        # serves on :5000 instead of :8080
```

Run the test suite from the repository root:

```
python -m unittest discover -s tests -v
```

## Verify it's up

```
curl http://localhost:8080/generos
```

Done when this returns a JSON array of genre names (e.g. `["Rock", "Samba", ...]`), not an error page. If it hangs on startup, it's still parsing the CSV — give it a few seconds.

## Gotchas

- Editing `data/top/*.csv` requires a restart: it's read once at import time, not per-request.
- Every endpoint returns `json.dumps(...)` as a plain string, not `jsonify` — responses come back `Content-Type: text/html`. This is intentional legacy behavior; changing it is a real API change, not a cleanup.
- `/similares?sequencia=` now accepts lowercase chords and spaces; this is an intentional API change. Input is normalized before matching.
- Tests that import `main` must import `tests/isolamento_db` before `main`, so `SEQUENCIAS_DB_PATH` points to a temporary database and no real `db/` is created.
- The six original sequences come from the idempotent seed in `sequencias_db.py`, using `data/mapeamento_sequencias_famosas.txt`; they are no longer defined in `main.py`.
- The `SEQ_FAMOSA` tag in the CSV is only a regression oracle. Runtime matching and the sequence catalog do not depend on it.
- Check `docs/adr/` before changing the deploy setup — it has a documented reason for its current state.
