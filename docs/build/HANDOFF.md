# HANDOFF — Lorekeeper

Transferred from: Lorekeeper autonomous build (session 2), 2026-10-18.
This document is authoritative — including over memory and older summaries. Replace
any older HANDOFF.md with this one.

## 1. Snapshot

Lorekeeper (command `lore`) is a self-sufficient, standalone story-world engine, inspired by Aeon Timeline but in no way dependent on it.
- **Storage:** a world is plain Markdown files, one per character, place or event, with flat frontmatter and Obsidian wikilinks.
- **What it does:** reads dates at whatever precision they are written, computes ages and timelines, and checks continuity (FAIL means a definite error, WARN a possible one).
- **Interfaces:** a CLI, an MCP server for AI agents, and a local web editor.
- **Interop:** imports and exports Aeon `.aeon`, CSV and Markdown.

It was built for three audiences: writers who draft with AI agents, novelists who don't use AI, and worldbuilders/GMs. Its first clients are the owner's three novel sagas (Realm, Space, Zombies), which now use it in warn mode.

## 2. Current state

**Done.** Features 001–007 are built, reviewed and fixed.
- **Lorekeeper repo:** HEAD `aaf029b` at https://github.com/WilliamEbong/lorekeeper (PRIVATE). 190 tests pass. The CLI is installed with `uv tool install .`.
- **Standalone, confirmed 2026-10-18:** with the Aeon bundle hidden and no sagas reachable, the installed `lore` ran init, create, link, age, check, timeline, export to aeon/csv/md, re-import, MCP (20 tools) and the editor. The full suite passed, with 5 tests that need Aeon or the sagas skipping themselves. The package imports only the Python standard library.
- **Sagas:** integrated and landed. Live HEADs: Realm `efd585f`, Space `ffedb64`, Zombies `82a1536`. In-progress chapters have status/validate output identical to before the integration.

**In flight:** nothing.

## 3. Decision log

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| 1 | Stdlib-only Python, flat package, vendored into each saga | Sagas forbid reading outside their repo; zero dependencies | settled |
| 2 | Storage = the saga Wiki convention (flat keys, inline lists, quoted `"[[links]]"`) | A saga Wiki is a project with no conversion; byte-identical round trip | settled |
| 3 | Project config is `lore.json`, not TOML | The editor must write it; stdlib has no TOML writer | settled |
| 4 | Dates are intervals of integer minutes on one axis; no `datetime` | Precision and uncertainty without inventing detail | settled |
| 5 | Checks report only (FAIL definite / WARN possible); no auto-rescheduling | Never move canon silently | settled |
| 6 | Sagas run in **warn mode** | Nothing blocks the pipeline; fail mode is the owner's call | settled |
| 7 | Saga chronology config lives in `_system/lorekeeper.json` | The manifest is fingerprinted by in-progress profile packets | reversed → `_system/lorekeeper.json` (was a manifest key) |
| 8 | Roster pages of chapters in progress at integration keep their new dates deferred in `_system/knowledge/chronology_deferred.md` | Editing them staled those chapters' packets | settled |
| 9 | Canon gaps are decided and recorded in `agent_decisions.md` (42 birthdates) | Owner's standing rule; owner may override | settled |
| 10 | Ageless beings carry `max_age: none` | Immortals must not trip the 130-year limit | settled |
| 11 | `.aeon` writer emits fileVersion 14 (template shape) and lets Aeon migrate it | Avoids guessing the v27 shape | settled |
| 12 | Saga changes are made in clones and landed fast-forward only, back to back | Live repos and in-progress files stay untouched | settled |
| 13 | Aeon desktop app is not used | Owner declined access twice; Lorekeeper is standalone | settled |

## 4. Open questions

- Should the sagas switch from warn to fail mode? (Owner's decision.)
- Realm's rule "paired cards sit 7 days apart" has no structured pairing data yet, so it isn't encoded.
- A Lorekeeper-written `.aeon` has never been opened in the Aeon app (optional; the sample is at `C:\Users\Owner\lk-scratch\aeon_out`).

## 5. Next actions

1. Review the Space chronology report: Cards 051/052 (6840 CE, Day 168) after Card 050 (6842 CE, Day 164) on one rail, and four impossible SRD days (D366/D367/D374/D378) on cards 110, 111, 205 and 206. **← NEXT**
2. As Realm CH004, Space CH005 and Zombies CH004 freeze, apply their deferred keys from `chronology_deferred.md`.
3. At the next engine change, re-vendor Lorekeeper into the sagas (they carry `eb20b30`; `dc9207a` only adds a load speed-up) via clones and `land.sh`.
4. Optionally try `lore serve` on your own world, and `saga.py timeline` on a saga.

## 6. Constraints & preferences

- The owner directs in plain language and does not read code, JSON or git. Persisted docs and commits use normal prose.
- Ponytail (the simplest correct design) and stdlib only. Spec Kit for features (the `speckit-*` skills). Playwright for any UI check. Codex builds and reviews; Claude commits.
- **Sagas:**
  - Never stage in-progress chapters, `_system/state`, provenance or `saga.log`.
  - Engine commits are prefixed `system:`; authorities are read-only.
  - Run status/validate only on copies, because health and validate can rewrite status files.
- Nothing public. The only remote is the private repo.

## 7. Artifact manifest

| Artifact | Purpose | Status | Canonical location |
|----------|---------|--------|--------------------|
| Lorekeeper source + tests | The app (`lorekeeper/`, `tests/`) | final | repo (`Documents\Lorekeeper`, GitHub private) |
| README.md, docs/user-guide.md, docs/agent-skill.md | Owner, novelist and agent guides | final | repo |
| docs/research/AEON-SPEC.md | Clean-room `.aeon` format notes | final | repo |
| docs/build/BUILD-PLAN.md, SESSION-LOG.md | Plan with checklist; full build history and evidence | final | repo |
| docs/build/BUILD-NOTES.md | Previous handoff: Aeon research and saga engine seams | superseded | repo |
| specs/001–007 | Spec Kit specs, plans and tasks | final | repo |
| Saga chronology reports | Per-saga audit | final | each saga `_system/knowledge/chronology_report.md` |
| Saga helper scripts (land.sh, commit_system.sh, baseline.sh, …) | Safe saga updates | final | `C:\Users\Owner\lk-scratch\snap` (local only) |
| Sample `.aeon` export | Optional Aeon check | final | `C:\Users\Owner\lk-scratch\aeon_out` |

## 8. Glossary

- **Card:** an architecture chapter card. Lorekeeper models it as an in-memory item of type `card`.
- **Rail:** a Space story strand (`Primary allocation` field).
- **SRD:** Space's 365-day production calendar. `Y0 = 6842 CE`; written `SRD Y0 D004` or `6842 CE, Day 004`.
- **Warn mode:** chronology findings are printed but never block a stage.
- **Profile packet:** the saga's per-chapter character context. Its receipt hashes the manifest and roster pages.
- **Probe:** a full copy of a live saga, used for checks that may write files.
- **FAIL / WARN:** definite / possible continuity error.

## 9. Probe facts

1. The saga chronology config is `_system/lorekeeper.json`, not PROJECT_MANIFEST.json, because profile packets hash the manifest.
2. 42 birthdates were decided rather than sourced: Realm 18, Space 15, Zombies 9.
3. The sagas vendor engine `eb20b30`; the repo HEAD engine differs only by a load speed-up (3,000 items: 1.55 s → 0.85 s).

## 10. Appendix — embedded artifacts

None.
