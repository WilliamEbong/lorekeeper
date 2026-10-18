# KICKOFF PROMPT — start the autonomous Lorekeeper build

## How to start
1. Open a **new** Claude Code session (desktop Code tab or terminal) with its working folder set to:
   `C:\Users\Owner\OneDrive\Documents\Lorekeeper`
   (The project-scoped continuity hooks only load when the session starts in this folder.)
2. Nothing to add by hand: `.claude/settings.json` already grants the session access to these folders (`permissions.additionalDirectories`). If a folder is still refused, add it in the app:
   - `C:\Users\Owner\OneDrive\Documents\Creative writing`
   - `C:\Users\Owner\OneDrive\Documents\aeon timelin RE`
   - `C:\Users\Owner\lk-scratch` (it will be created)
3. Paste everything inside the box below as your first message.
4. If the session is interrupted (usage limit, crash, compaction), start or resume a session in the same folder and paste the **resume prompt** at the bottom.

---

## Prompt (paste this)

```
Build Lorekeeper autonomously, to completion. Do not stop to ask me anything except the stop conditions listed in the plan.

FIRST, before any other action, read these three files in full, in this order:
1. docs/build/HANDOFF.md        (everything learned so far, plus the decisions)
2. docs/build/BUILD-PLAN.md     (the approved plan, the "Design-review amendments" that SUPERSEDE the plan text, and the progress checklist)
3. docs/build/SESSION-LOG.md    (history; append to it)

THEN regenerate the plan. Re-validate BUILD-PLAN.md against the actual state of this folder, the three saga repos, and the tools (versions, Spec Kit, REA MCP, Codex plugin). Fix anything stale in BUILD-PLAN.md, log what you changed in SESSION-LOG.md, then start at the first unticked checklist box.

How to work:
- Spec Kit. Use the exact init sequence in the plan (Phase 0). Each feature 001–007 goes through speckit-specify → plan → tasks → implement → converge. Keep claude as the active integration.
- Ponytail: the laziest correct design. Stdlib only in Lorekeeper. Run a ponytail-review at the end of each feature.
- REA MCP/CLI for the remaining Aeon work. Re-extract the bundle with tools/aeon_extract.py into scratch, never into the repo. Write docs/research/AEON-SPEC.md in your own words.
- Codex. Loop it in heavily through Agent(subagent_type "codex:codex-rescue") with --write, using self-contained briefs: Codex works only inside this repo, never commits, never pushes, never installs. Codex builds the well-specified modules and tests, and does a read-only adversarial review per feature. You write the specs, the saga integration and the verification, and you do all commits. After every Codex run, check git status in Lorekeeper and all three sagas for stray changes.
- Computer use: open our exported .aeon files in the Aeon Timeline desktop app (and create sample .aeon fixtures there early). Never enter licence or account details.
- Playwright MCP verifies every editor/UI change. context7 is used before writing code against any library or spec (e.g. the MCP protocol version).
- Saga integration happens only in clones under C:\Users\Owner\lk-scratch\sagas. Take baselines first. Land it into the live repos by fast-forward merge only. Never stage the in-progress chapters (Realm CH004, Space CH005, Zombies CH004), state files or saga.log. Commit engine changes as "system:". Backfill frozen-chapter Wiki data autonomously, and record invented facts in each saga's agent_decisions.md.
- Make judgement calls yourself. Log each assumption or decision as one line in SESSION-LOG.md and keep going.

Continuity (non-negotiable):
- Phase 0 installs the project-scoped hooks (tools/build-hooks/guard.py, amendment 12) and creates docs/build/ACTIVE.
- Rewrite HANDOFF.md and append to SESSION-LOG.md at every Spec Kit step and every feature boundary. Tick BUILD-PLAN.md boxes as they complete. Commit often.
- When a hook warns of 90%, 94% or 97% context, or you sense context is getting long: finish the current atomic step, then immediately update HANDOFF.md, SESSION-LOG.md and BUILD-PLAN.md, and commit.
- After any compaction or restart, re-read all three docs before acting. The pre-edit hook enforces this.

Definition of done: features 001–007 converged; all verification in the plan passes (unittest; the 3 saga suites + parity; Playwright editor flows; .aeon opening in Aeon; the MCP golden test); the three sagas are integrated in warn mode with chronology reports generated; docs are written (README, user guide, agent skill); the private GitHub repo is created with gh and pushed (private only, nothing public); HANDOFF.md is final; ACTIVE is removed and the hooks are unregistered; memory is updated. Then give me a plain-language final report: what was built, where it is, what it found in my sagas, and the decisions you made.

Stop only when done, or for the plan's stop conditions: anything that would be public; a cryptographic .aeon trailer; an Aeon licence prompt; a saga baseline that is already red; a destructive or outward action not covered by the plan.
```

---

## Resume prompt (after any interruption)

```
Resume the Lorekeeper build. Read docs/build/HANDOFF.md, docs/build/BUILD-PLAN.md and the last 150 lines of docs/build/SESSION-LOG.md first. Check git status/log to confirm where you stopped, then continue autonomously from the first unticked box, following the same rules as the kickoff prompt in docs/build/KICKOFF-PROMPT.md. Stop only when done.
```
