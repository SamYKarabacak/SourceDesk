# Working on SourceDesk

Start with the setup and development commands in the README. Keep the existing
`data/` folder out of commits, and use temporary data directories for tests.

## Code map

- `run.py` owns first-run setup, loopback startup, and offline restore.
- `backend/main.py` serves the API and static interface.
- `backend/extraction.py` preserves source offsets while reading and splitting files.
- `backend/storage.py` owns SQLite, FTS5, history, and embedding persistence.
- `backend/retrieval.py` ranks passages and builds the semantic cache.
- `backend/research.py` coordinates uploads, searches, and cited answers.
- `backend/ollama.py` implements the local model HTTP protocol.
- `backend/jobs.py` runs one cancellable indexing job at a time.
- `backend/backup.py` snapshots and validates portable workspaces.
- `frontend/` contains plain HTML, CSS, and JavaScript, with no build step.

## Changes

Prefer small functions with explicit inputs. Keep user-visible errors in plain
language. Treat extracted document text as data: render it with text nodes, never
as HTML. Do not add network calls to the document-search path.

Source IDs and offsets must remain valid across upgrades. Derived indexes can
be rebuilt; original text and saved evidence cannot. Schema changes need a
migration fixture and a test that reopens a previous workspace. Existing
configuration prefixes must continue to work.

Add regression tests for behavior that was broken or changed. Model adapters in
the automated suite are simulated; do not describe those results as live model
quality measurements. Run the Python checks and retrieval sample for backend
changes, and the browser workflow for interface changes.

## Releases

Update the version in `backend/__init__.py` and `pyproject.toml`, the interface
footer, launcher banner, changelog, and verification notes. Run the checks, then
build `releases/SourceDesk-v<version>.zip` with `scripts/package.py`. The archive
is reproducible for identical source files and includes no local workspace.
