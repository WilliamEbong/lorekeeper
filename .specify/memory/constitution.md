# Lorekeeper Constitution

## Core Principles

### I. Stdlib-only, vendorable core
Lorekeeper is pure Python ≥3.11 that imports nothing outside the standard library. The package must still work when copied flat into another repository (the sagas vendor it into `_system/vendor/lorekeeper/`). That means relative imports only, no package data loaded by path tricks, no entry-point magic. Project configuration is `lore.json`, which is read and written with `json`.

### II. Plain text is the source of truth
- **One item, one file.** Each story-world item is one Markdown file. Its frontmatter uses flat `[a-z_]+` keys whose values are scalars or inline lists. Links are quoted wikilinks (`"[[Name]]"`). This is the saga Wiki convention and Obsidian Properties compatible.
- **Byte-stable writes.** Lorekeeper never rewrites bytes it did not mean to change. A read followed by a write with no edits must reproduce the file exactly, line endings included.
- **No hidden store.** There is no database, cache file or index that can disagree with the text.

### III. One operations table, three faces
- **One table.** Every capability is defined once, in a single operations table (name, parameters, handler, read/write flag).
- **Three faces.** The CLI (argparse, `--json`), the MCP server (stdio JSON-RPC, tools only) and the editor's HTTP API are thin adapters over that table.
- **Identical output.** For the same operation, the CLI with `--json`, MCP and HTTP all return the same data.

### IV. Never lose an edit
- **Atomic writes.** Write a temp file, then replace, with one retry for OneDrive locks.
- **Versioned writes.** Every read returns the file's sha256 as its version, and every write states the version it was based on.
- **Conflicts.** A concurrent change to different keys is merged. A conflicting change is refused (409), and the caller keeps their input.
- **Saga canon.** In saga mode, human edits become change requests and never touch canon directly.

### V. Honest checks
- **Severity by certainty.** A definite violation is `FAIL`; a merely possible one, given date uncertainty or provisional status, is `WARN`.
- **Finding format.** Every finding carries a code, a severity and a `file:line`.
- **Exit code.** Any FAIL exits non-zero.
- **No silent fixes.** Lorekeeper checks; it never silently reschedules anything.

### VI. Ponytail simplicity
Climb the ladder: does it need to exist? Is it already here? Does stdlib do it? Use the smallest correct code. There are no interfaces with one implementation, no config for values that never change, and no scaffolding for later. A deliberate shortcut with a known ceiling gets a `ponytail:` comment.

### VII. Tests that bite
- **unittest only.** Tests use stdlib `unittest` (`python -m unittest discover -s tests`).
- **One check per piece of logic.** Each piece of non-trivial logic (a parser, calendar maths, a check, a merge) keeps at least one runnable test that fails if the logic breaks.
- **Standing tests.** A stdlib-only import scan and a no-bare-`open(` scan are permanent tests.

## Constraints
- **Security.** `lore serve` binds to 127.0.0.1 only. It checks the Host header, and mutating requests need a per-run token plus a JSON content type. Nothing is fetched from a CDN.
- **Text I/O.** Text is UTF-8 everywhere: every `open()` in text mode passes `encoding="utf-8"`.
- **Aeon data.** Content extracted from Aeon Timeline never enters this repository. The interop code is written from our own clean-room spec (`docs/research/AEON-SPEC.md`).
- **Publishing.** Nothing is ever published or pushed, except the approved private GitHub repository at the end of the v1 build.

## Development Workflow
- **Spec Kit.** Each feature runs speckit-specify → plan → tasks → implement → converge, then a ponytail review and an independent adversarial review.
- **Commits.** They follow `<type>: <description>`. Engine changes inside a saga are committed as `system:` and never ride along with chapter freezes.
- **Saga integration.** It is developed in clones and landed by fast-forward merge only. It never stages in-progress chapters, state files or logs.

## Governance
This constitution outranks other guidance for Lorekeeper code. An amendment needs a dated entry in `docs/build/SESSION-LOG.md` and a version bump here. Reviews check every change against principles I–VII.

**Version**: 1.0.0 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-18
