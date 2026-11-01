# Persist the custom sequence catalog in SQLite

The app currently recognizes only the six chord sequences hardcoded in
`main.py:40-45`. The CSV column `SEQ_FAMOSA` carries a precomputed tag that the
search endpoint reads, so the catalog cannot grow without editing code and
regenerating data. The custom-sequences feature requires any visitor to register
a sequence, requires the catalog to survive server restarts, and requires it to
grow without a new deploy. The task also fixes two boundaries: the music and
genre catalogs keep coming from `data/top/dataset_final.csv` in memory, and the
application keeps running as the single local-only Docker container described in
ADR 0001.

We decided to store the sequence catalog in SQLite, using the `sqlite3` module
from the Python standard library, while leaving music and genre data in the CSV.
The database path is configurable through the `SEQUENCIAS_DB_PATH` environment
variable and defaults to `db/sequencias.db`; the `db/` directory is ignored by
both Git and Docker. A single `sequencias` table holds the catalog, and startup
creates the table and seeds the six built-in sequences idempotently using the
names in `data/mapeamento_sequencias_famosas.txt`. Matching no longer reads
`SEQ_FAMOSA`; the tag remains in the CSV only as the regression oracle for the
six original sequences.

SQLite is a good fit because it is already available in Python, needs no extra
service or pip dependency, gives us transactions and a single-file store, and
fits the one-container, local-only deployment in ADR 0001. A JSON or TinyDB
store would offload atomicity and locking to the application, and an external
database would violate the constraint against additional services.

This choice has consequences. The Docker run must mount a named volume at the
database directory, for example `-v ciframe-db:/app/db`; without it, `docker rm`
and a fresh `docker run` lose the catalog even though `docker restart` keeps the
container's writable layer. The first startup seeds the six original sequences,
so the catalog is never empty for the existing search behavior. SQLite
serializes writes, which means concurrent registrations wait for one another;
that is acceptable for the local, low-concurrency use case. The database is a
mutable runtime artifact, not part of the image, so schema changes in the future
will need a migration plan rather than a rebuild alone.
