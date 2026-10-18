# Lorekeeper

Before anything, read docs/build/HANDOFF.md, docs/build/BUILD-PLAN.md and the tail of docs/build/SESSION-LOG.md. They hold the current position, the plan and its checklist, and the history.

Spec Kit project: plan and build features with the speckit-* skills (constitution once; then specify → plan → tasks → implement → converge). Do not use superpowers brainstorming, writing-plans, executing-plans, or subagent-driven-development here; superpowers debugging, TDD, and verification skills are still fine.

## Project rules
- Lorekeeper itself is stdlib-only Python (≥3.11). No third-party imports, ever. It is vendored into the user's saga repos.
- Every `open()` passes `encoding="utf-8"` (binary mode excepted).
- Tests use `unittest`: `python -m unittest discover -s tests`.
- Never push anywhere except the approved private GitHub repo at the end of the build. Never make anything public.
- Extracted Aeon Timeline content stays in `C:\Users\Owner\lk-scratch`, never in this repo.
