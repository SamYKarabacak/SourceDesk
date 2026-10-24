# Changelog

## 1.0.0 — 2026-10-25

SourceDesk is the first stable release of the application previously named BraveTrace.

- Add a Windows launcher and a portable Python launcher that set up dependencies,
  open the browser, and select a free loopback port.
- Add workspace ZIP backups using a consistent SQLite snapshot, including WAL data.
- Add offline restore with checksum, path, database, and reference validation.
  Existing workspaces are never overwritten.
- Continue batch uploads after a failed file and report individual failures.
- Show semantic index coverage and expose a full rebuild in the AI setup guide.
- Keep research usable when browser session storage is blocked.
- Add `SOURCEDESK_*` settings while preserving both previous configuration prefixes,
  the database filename, source IDs, saved research, and cached vectors.
- Refresh the name, document icon, interface accents, accessibility labels, and
  reduced-motion behavior. Prevent stale API responses from being cached.
- Add reproducible source packaging and extend backend and browser regression checks.

## 0.2.0

- Prefer paragraph boundaries when splitting uploads; use 700-character passages
  with 120 characters of overlap.
- Add English stemming, query-coverage filtering, numeric constraints, and FTS snippets.
- Save the latest 100 research results and export full source passages as Markdown.
- Build embeddings in a background job with progress, cancellation, and cached resume.
- Retry invalid AI formats or citations once before withholding the answer.
- Add a mobile library toggle and compact results.
- Migrate v0.1 databases without changing source IDs or cached embeddings.

## 0.1.0

Initial PDF, TXT, and Markdown uploads, SQLite search, source inspection, Ollama
integration, hybrid retrieval, and browser interface.
