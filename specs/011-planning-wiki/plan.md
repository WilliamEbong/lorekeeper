# Plan: Feature 011, planning wiki

Spec: [spec.md](spec.md). Tasks: [tasks.md](tasks.md).

## Technical context
- Python ≥ 3.11, standard library only; vanilla JavaScript editor under its strict CSP; `unittest`.
- Builds on feature 010: `wiki.sections` (facts and sections), `wiki.number` (fact ids), `wiki._split` (line-ending-safe edits), `wiki.LINK/plain/norm`, `store.atomic_write` (versioned writes), the `request` op, the Wiki tab, `--config`, `lore mcp --saga`.
- Constitution check: I (stdlib, relative imports) yes; II (plain text, byte-stable: edits go through `_split`, which keeps CRLF/LF; no cache file, link lists computed on read) yes; III (five new ops in the one table) yes; IV (versioned writes, CONFLICT; saga editor edits become requests) yes; V (planning problems carry code, severity, file:line) yes; VI (one new module, no new abstractions) yes; VII (TDD tests per piece of logic) yes.

## Design
One new module, `lorekeeper/planning.py`, built once per project like `wiki.story(p)`:

- **Settings** `settings(p)`: validates `planning_wiki` (FR-1) into `folder` (absolute), `sources` (list of dicts with `name`, `path`, `rank`, `role`), `exclude` (lower-cased set). Errors are `LoreError("INVALID", ...)` naming the key.
- **Source reader** (`Source` class, read lazily once per project): `outline()` parses headings (fence-aware), each with `ref` (leading number token, `§` stripped, must contain a digit), `title`, `level`, `line`, `end`; overrides registers also yield `**ID:** \`HO-NNN\`` blocks as sections. `find(ref)`: number exact, then normalized title exact, then title prefix; ambiguity raises with candidates. `text(section)`.
- **Citations** `cite(text)`: trailing `[src: a; b]` → (text, [refs]); `resolve(ref)` → `{source, section, title, rank, found}` by longest source-name prefix (case-insensitive).
- **Pages**: walk the folder like `Story._companions`; frontmatter must have `type`. Attach to an item by `page` link or name (`p.resolve`). `Entry` holds names (canonical, aliases, item name and aliases), parsed sections (`wiki.sections` + `wiki.number`), decided facts and ideas.
- **Name matcher** `Matcher(entries, exclude)`: one compiled alternation of all usable names (≥ 3 letters, not excluded), longest first, `(?<![\w])name(?![\w])`, case-sensitive; maps a hit back to entries. Used for dialogues, appears-in, ideas.
- **Link lists**: members by backlinks (`kind`, `member_of` in planning or item fields) and `member_tags`; dialogues from `dialogues` sources (entry heading level = deepest heading level in the file; headings and speaker labels `^\*\*([^*:]+?)(?: \([^)]*\))?:\*\*`); appears-in from `chapters` sources (`^#{1,6}\s+Chapter\s+(\d+)\s*[:.—-]?\s*(.*)`, body to the next heading, minus `skip` lines) and narrative items; ideas from `ideas` sources, by heading only.
- **Views**: `index()` (groups, `problems`), `card(ref)`.
- **Problems** (FR-4): computed in `index()`.
- **Edits**: `fact(...)` for `planning-fact` (add/replace/remove, create page with `--type`), reusing `wiki._split` and `atomic_write` with the page version; `impact(...)`; `change(...)`.
- **Impact** (FR-8): case-insensitive whole-phrase regex over decided planning facts, each non-idea source line by line (mapped to its innermost section), chapter cards and prose files (`prose` pattern formatted with `n`, for n ≤ written + 1 only), project items, and story pages via `wiki.story(p)` facts (with their from-chapter). Grouped, capped by `limit`.
- **Change** (FR-9): read and validate all targets first (page version, source file and section, register); next id = max `HO-(\d+)` + 1 (3 digits); register block appended in the register's own style (`---` separator, bold labels); amendment blockquote inserted after the last non-blank line of the section; page fact replaced with `[src: Overrides HO-NNN; <old refs>]`; impact; Markdown `report`.

`ops.py`: five ops (`planning`, `planning-source`, `planning-fact`, `planning-impact`, `planning-change`) with AI guides; `request` accepts `plan:` keys. `store.files()` skips the planning folder. `mcp.py`: `offered()` gives `planning`, `planning-source`, `planning-impact`, `planning-fact` in saga mode; `planning-fact` needs a planning folder in the settings; `planning-change` FORBIDDEN with how-to. `cli.py`: human text for the five ops (the change prints the report). `serve.py`: live-reload stamp includes the planning folder and source files' mtimes. Editor: picker option, planning index/card renderer, citation dialog, change form; saga mode builds a `request`.

## Files
- New: `lorekeeper/planning.py`, `tests/test_planning.py`, fixture `tests/fixtures/planning/` (bible, conversations, outline, ideas, register, Wiki items, planning pages, settings).
- Changed: `ops.py`, `mcp.py`, `cli.py`, `store.py`, `serve.py`, `editor.js`, `editor.html`, `editor.css`, `tests/test_mcp.py`, README, `docs/user-guide.md`, `docs/agent-skill.md`.

## Saga integration (run-4 method)
1. Before-baseline on fresh probes (`lk-scratch/run5-before`): suites, status/validate/health per chapter, tree hashes of Wiki, Story Wiki, roles, templates, skills, workflow; packets verify.
2. Fresh clones (`lk-scratch/sagas5`), re-vendor engine, add `planning_wiki` key, shared skill + README row + one pointer, `system:` commit.
3. Three parallel subagents build each saga's `Planning Wiki/` with `planning-source` and `planning-fact` (or page files in the format, then `lore planning` problems must be 0); `wiki:` and `knowledge:` commits.
4. Replay onto probes; after-baseline must equal before (outside the new paths); Playwright on `saga.py timeline`; MCP handshake.
5. Change-flow proof on a probe copy: edit → override → write-back → impact → refresh-sources → frozen flags; report sent.
6. Reviewers; land with `land.sh` (fast-forward only), live HEADs re-checked.

## Risks
- Large documents: the reader parses once per project instance; the editor's server rebuilds the project on change only.
- Ordinary-word names: exclusion list plus case-sensitivity plus the three-letter floor; the build agents record any exclusions they add as decisions.
- `written` default from the Story Wiki can lag; the saga skill passes it explicitly.
