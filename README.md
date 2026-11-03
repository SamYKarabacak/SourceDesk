# SourceDesk

Search documents on your computer and open the passages behind each result.
Import PDFs, Markdown, or text files, then search for a topic or ask a question.
Documents and saved research stay on your computer.

**Version 1.0.0 · Created by SamYKar / BravenDev · MIT license**

## Start the application

Install [Python 3.12 or newer](https://www.python.org/downloads/), then download
and extract [SourceDesk-v1.0.0.zip](releases/SourceDesk-v1.0.0.zip).
Extract the whole folder before starting; do not run files from inside the ZIP.

On **Windows**, double-click **Start-SourceDesk.cmd**. On **macOS or Linux**, open
a terminal in the extracted folder and run:

```bash
python3 run.py
```

The launcher creates a Python environment, installs the required packages, starts
the local server, and opens your browser. The first start needs internet access
for packages. After setup, document search works offline. Keep the terminal open;
press **Ctrl+C** to stop the application. There is no account or subscription.

If the browser does not open, use the address printed in the terminal. The
launcher uses the first free port from 8000 to 8010. For a specific port:

```text
python run.py --port 8011 --no-browser
```

Use `py -3` instead of `python` if that is how Python is installed on Windows.
On Debian/Ubuntu, install the system's `python3-venv` package if Python reports
that virtual environments are unavailable.

## Use your workspace

1. Choose **Add documents**, drop files into the library, or select **Try sample documents**.
2. Enter search terms or a question. **Search** finds passages; **Evidence** presents matching sources.
3. Open a source card to read the highlighted passage in context or download the original file.
4. Select a document in the sidebar to search only that document. Choose **All documents** to clear the scope.
5. Reopen saved results from **Recent research**, or choose **Export notes** for a Markdown copy with source text.

Keyboard shortcuts: **Ctrl+Enter** (Command+Enter on macOS) submits a question;
**/** focuses the question field. **Escape** closes a dialog.

A batch upload continues after a rejected file and reports which files failed.
Identical files are detected by content, even if their names differ.

## Optional local AI

Evidence search needs no model. AI answers and hybrid search use
[Ollama](https://ollama.com/download), running on your own computer:

```text
ollama pull qwen3:4b
ollama pull embeddinggemma
```

Open the **?** setup guide and choose **Refresh AI status**. Select **AI answer**
to generate an answer from retrieved evidence. For **Hybrid search**, first choose
**Build semantic index**. Progress is displayed, and indexing can be stopped and
resumed without losing completed batches. Keyword search stays available during a build.

If you replace an embedding model under the same name, use **Rebuild semantic
index** in the setup guide. A rebuild resets its cached vectors; documents and
saved research are retained.

The model must support Ollama's structured JSON output and `think: false`.
Source references are validated before an AI answer is shown. This checks which
passages were cited; it cannot establish that every claim follows from them.
Live model answer quality has not been benchmarked. Model downloads can be
several GB, and inference speed depends on your hardware. Check model licenses separately.

## Back up and restore

Choose **Back up workspace** to download a ZIP containing original files, extracted
text, source references, research history, and cached embeddings. The backup
includes committed SQLite WAL data and checks the originals before packaging them.
Save the ZIP outside the application folder.

To restore, stop the application and choose a **new, empty** data folder:

```text
python run.py --restore "SourceDesk-backup-2026-10-25.zip" --data-dir "restored-data"
```

The date above is an example; use your backup's actual filename. Restore verifies
the archive layout, database integrity, document checksums, and references before
moving the workspace into place. It refuses to overwrite existing files. Restore
supports archives up to 1 GB uncompressed.

For subsequent starts with that workspace, run:

```text
python run.py --data-dir "restored-data"
```

Backups are unencrypted and contain your document contents. Keep them private.

## Configuration and upgrades

By default, data is stored in `data/` next to `run.py`. Choose another location with
`--data-dir` or set environment variables before launching:

| Variable | Default | Purpose |
|---|---|---|
| `SOURCEDESK_DATA_DIR` | Project `data/` folder | Documents, database, and history |
| `SOURCEDESK_CHAT_MODEL` | `qwen3:4b` | Ollama answer model |
| `SOURCEDESK_EMBEDDING_MODEL` | `embeddinggemma` | Ollama embedding model |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama HTTP address |

An `.env` file is not loaded automatically. `.env.example` lists the settings for reference.

SourceDesk continues the BraveTrace / EvidenceLens application. Existing
`BRAVETRACE_*` and `EVIDENCELENS_*` settings still work, with precedence
`SOURCEDESK_*` → `BRAVETRACE_*` → `EVIDENCELENS_*`. The database remains named
`evidencelens.sqlite3`, preserving documents, source IDs, history, and vectors.

Before upgrading, stop the old server and back up the entire data folder.
Keep that folder in place, copy it into the new application folder, or point
`--data-dir` at its existing location. Do not run two servers against the same workspace.

## Scope

SourceDesk is a single-user local application. It binds to the loopback interface;
it has no hosted service, telemetry, or remote model API. Original files and
research are stored unencrypted. Limits are 50 documents, 10 MB per file, 300 PDF
pages, and one million extracted characters per document.

Scanned PDFs need OCR before import. Complex layouts and tables can extract
poorly. Keyword search uses English stemming and may miss partial matches;
hybrid search can return weak semantic matches. Always inspect the sources.

## Development

```text
python run.py --check
.venv/bin/python -m pip install -r requirements-dev.txt -c requirements-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python scripts/evaluate.py
npm ci
npx playwright install chromium
npm run test:browser
npm run check:frontend
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
Node.js is needed only for browser tests and frontend formatting. To start the
server directly, use `.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`.

Build the distributable with `.venv/bin/python scripts/package.py`. It excludes
workspaces, virtual environments, caches, and previous archives. The ZIP includes
the source, launchers, examples, tests, dependency pins, and documentation.

See [architecture](docs/ARCHITECTURE.md), [contributing](docs/BUILD_FROM_SCRATCH.md),
[verification](docs/VERIFICATION.md), and the [changelog](CHANGELOG.md).
