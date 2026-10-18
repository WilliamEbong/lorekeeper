# Lorekeeper — agent rules

Before anything, read docs/build/HANDOFF.md (and, for detail, BUILD-PLAN.md and the SESSION-LOG tail).

Spec Kit project: plan and build features with the speckit-* skills (constitution once; then specify → plan → tasks → implement → converge). Do not use superpowers brainstorming, writing-plans, executing-plans, or subagent-driven-development here; superpowers debugging, TDD, and verification skills are still fine.

## Rules for Codex (and any other agent handed a task here)
- Work only inside this repository (`C:\Users\Owner\OneDrive\Documents\Lorekeeper`). Never read from or write to the saga repos under `Documents\Creative writing` unless the brief explicitly says to read a named file.
- Never run `git commit`, `git push`, `git add`, or any git command that changes history or the index. Claude commits.
- Never install anything (no pip, uv, npm, winget).
- Lorekeeper is stdlib-only Python (≥3.11). No third-party imports.
- Every `open()` passes `encoding="utf-8"` (binary mode excepted). Read text with `newline=""` when line endings matter.
- Use `unittest`, not pytest. Run `python -m unittest discover -s tests` before reporting, and report the result.
- Keep it simple: the smallest correct code, no speculative abstractions.
- Finish with a list of every file you created or changed.
