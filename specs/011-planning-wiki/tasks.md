# Tasks: Feature 011, planning wiki

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md). TDD: each engine task writes its failing tests first.

## Phase 1: engine (lorekeeper/planning.py)
- [x] T001 Fixture world `tests/fixtures/planning/` (settings with every source role, bible, conversations, outline with Meanwhile lines, plot ideas, register, Wiki items with tags, planning pages incl. a kind with member_tags, an excluded ordinary-word name, a short name, an Ideas section, a unique leak marker) (SC-2)
- [x] T002 Settings validation and errors (FR-1)
- [x] T003 Source reader: outline, numbers, titles, `§`, levels, fences, override ids, ambiguity, missing file (FR-6, SC-1)
- [x] T004 Citations and ref resolution (FR-3)
- [x] T005 Pages, attachment to items, names; store scan skips the planning folder (FR-2)
- [x] T006 Name matcher: whole word, case-sensitive, three-letter floor, exclusion list (FR-5)
- [x] T007 Link lists: members, dialogues, appears-in (skip lines, narrative items), idea sections (FR-5)
- [x] T008 Index with problems; card with sections, ideas, links (FR-4, FR-5)
- [x] T009 planning-fact add/replace/remove/create, CONFLICT, refusals (FR-7)
- [x] T010 planning-impact groups, statuses, limit, ideas never searched (FR-8)
- [x] T011 planning-change: validation first, register entry, write-back (LF and CRLF), fact update, report (FR-9)
- [x] T012 Leak tests: marker never in wiki (both modes), query/show/graph/export/check (FR-15)

## Phase 2: faces
- [x] T013 Ops with AI guides; `request` accepts planning keys (FR-10, FR-16)
- [x] T014 MCP saga offering and refusals; golden test extended (SC-3)
- [x] T015 CLI human text (planning, source, impact, change report)
- [x] T016 serve live-reload stamp covers the planning folder and sources (FR-14)
- [x] T017 Editor: picker Planning, planning index and card, citation dialog, labelled ideas, link lists, change flow local and saga (FR-11 to FR-14)
- [x] T018 Playwright (fixture): light, dark, 390 px, console; Impeccable detector (SC-4)
- [x] T019 Timing on Realm's real documents (SC-5)

## Phase 3: docs
- [x] T020 README, user guide, agent skill (FR-17)

## Phase 4: sagas
- [x] T021 Before-baseline on fresh probes; fresh clones (FR-21)
- [x] T022 Clones: re-vendor, `planning_wiki` key, shared skill `planning_wiki_change.md`, README row, one pointer; `system:` commits (FR-18, FR-19)
- [x] T023 Three parallel agents build the Planning Wikis; verify problems 0; `wiki:` and `knowledge:` commits (FR-18)
- [x] T024 Replay on probes; after-baseline equal; Playwright `saga.py timeline` Planning; MCP handshake (SC-6, SC-7)
- [x] T025 Change-flow proof on a probe copy; impact report (FR-20, SC-8)
- [x] T026 Reviewers (Lorekeeper diff; saga diffs with spot-checks and leak check); fixes
- [x] T027 Land fast-forward only (FR-21)
- [x] T028 Final checks, docs, handoff, memory, cron deleted, notification (SC-9)
