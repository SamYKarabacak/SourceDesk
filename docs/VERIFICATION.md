# Verification

## Version 1.0.0

Local release checks were run with Python 3.12.14, SQLite 3.53.1, Node.js 24.22.1,
and Chromium 153.0.8010.0 on Linux.

| Check | Result |
|---|---|
| Python regression suite | 122 passed |
| Keyword retrieval sample | 18/18; answerable-query MRR@5 1.000 |
| Python dependency consistency | `pip check` passed |
| Python lint and formatting | Ruff passed |
| JavaScript syntax and formatting | Node syntax check and Prettier passed |
| Browser workflow | Passed on desktop (1440 px) and mobile (390 px) |
| Fresh ZIP installation | Passed in a path containing spaces, with runtime dependencies only |
| Launcher restore and repeat start | Passed without reinstalling dependencies |
| Windows/Linux, Python 3.12/3.15 | Configured in GitHub Actions; see the current run |

The original checkout passed 94 tests before the V1 changes. The expanded suite
adds workspace backup and restore, archive validation, configuration precedence,
launcher behavior, and reproducible distribution checks.

## Browser workflow

The browser test owns a temporary application server, data directory, and
simulated Ollama HTTP service. It checks:

- Samples and duplicate detection; mixed uploads continue after an invalid file.
- Library filtering and scope, keyboard submission, ranked results, source
  highlighting, and original-file downloads.
- Workspace ZIP downloads and cited Markdown exports.
- Literal rendering of HTML and backticks from documents.
- Background indexing, search during a build, reload, cancellation, cached resume,
  coverage display, and a full index rebuild.
- AI response repair, clickable citations, and saved answers reopened offline.
- Document deletion removes related history and keeps unrelated saved results.
- Mobile layout, history deletion, and operation with browser session storage blocked.

Desktop and mobile screenshots were inspected for layout and clipping. No
JavaScript errors were observed in either the normal or storage-restricted session.

## Backup and upgrade checks

A workspace with documents, an AI answer, source IDs, and cached vectors was
exported and restored into a separate directory. The reopened workspace retained
the same storage counts, source content, history, and original bytes, without
making model calls. An empty workspace also round-tripped correctly.

The suite rejects missing or modified originals, changed databases, unexpected
archive paths, malformed manifests, and an invalid SQLite file. Failed restores
leave no partial workspace, and existing directories with contents are refused.
Packaging checks exclude local workspaces, environment files, dependencies, and
caches, and confirm identical source produces an identical ZIP.

Compatibility tests reopen existing research through each of `EVIDENCELENS_*`,
`BRAVETRACE_*`, and `SOURCEDESK_*`. The v0.1 schema fixture continues to verify
migration without changing original source IDs or cached embeddings.

## What these results mean

The retrieval sample contains three fictional documents and 18 questions written
alongside the application. It is a regression sample, not a held-out relevance
benchmark or a measurement of large-library performance.

All automated model calls use a fake adapter, HTTP mock transport, or simulated
HTTP service. They verify protocol integration, retries, citation validation,
indexing, and error handling. **No live Ollama inference was run for this release.**
Real answer quality, hallucination rates, and performance depend on the chosen
models and hardware and require a separate evaluation.

OCR, complex PDF tables, multilingual relevance, and large libraries are outside
these checks. A valid citation identifies a real supplied source; it does not
prove that an answer interprets that source correctly.

## Reproduce

Use the development commands in the README. The workflow runs the Python suite,
launcher setup, dependency checks, retrieval sample, and packaging on Windows and
Linux with Python 3.12 and 3.15. A separate Linux job runs the browser workflow.
The current results are in [GitHub Actions](https://github.com/SamYKarabacak/SourceDesk/actions).

The browser runner accepts `SOURCEDESK_PYTHON`,
`SOURCEDESK_BROWSER_EXECUTABLE`, and `SOURCEDESK_SCREENSHOT_DIR` for an existing
interpreter, Chromium binary, and screenshot output folder.
