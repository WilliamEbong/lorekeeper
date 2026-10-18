"""Continuity guard for the Lorekeeper build session (project-scoped Claude Code hooks).

Usage: python -I guard.py start|post|pre|compact   (hook JSON on stdin)

Every mode is a no-op unless docs/build/ACTIVE exists, and exits 0 on any internal
error. The one deliberate exception is `pre`, which exits 2 to block Edit/Write until
HANDOFF.md, BUILD-PLAN.md and SESSION-LOG.md have been read since the latest SessionStart.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DOCS = ("HANDOFF.md", "BUILD-PLAN.md", "SESSION-LOG.md")
TIERS = (  # fraction of the effective window, label, message
    (0.86, 86, "CONTEXT 86% (advisory): plan to reach a clean stopping point soon."),
    (0.90, 90, "CONTEXT 90% (mandatory): finish the current atomic step, then rewrite "
               "docs/build/HANDOFF.md, append SESSION-LOG.md, tick BUILD-PLAN.md boxes, and commit."),
    (0.92, 92, "CONTEXT 92% (final): compaction is close. Rewrite docs/build/HANDOFF.md NOW, "
               "append SESSION-LOG.md, commit. This repeats until HANDOFF.md is newer than this warning."),
)
TAIL_BYTES = 4 * 1024 * 1024


def build(root, *parts):
    return os.path.join(root, "docs", "build", *parts)


def load_state(root):
    try:
        with open(build(root, ".hookstate.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_state(root, state):
    with open(build(root, ".hookstate.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)


def window(state):
    env = int(os.environ.get("ECC_CONTEXT_WINDOW_TOKENS") or 1_000_000)
    return min(env, state.get("window") or env)


def transcript_tokens(path):
    """Tokens in context: last assistant usage plus bytes written after it / 4."""
    if not path or not os.path.isfile(path):
        return 0
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - TAIL_BYTES))
        lines = fh.read().split(b"\n")
    after = 0
    for raw in reversed(lines):
        if b'"usage"' in raw and b'"assistant"' in raw:
            try:
                entry = json.loads(raw)
            except ValueError:
                after += len(raw)
                continue
            usage = (entry.get("message") or {}).get("usage")
            if entry.get("type") == "assistant" and usage and not entry.get("isSidechain"):
                return (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0) + after // 4)
        after += len(raw) + 1
    return after // 4


def last_user_message(path, limit=1500):
    if not path or not os.path.isfile(path):
        return ""
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        fh.seek(max(0, fh.tell() - TAIL_BYTES))
        lines = fh.read().split(b"\n")
    for raw in reversed(lines):
        if b'"user"' not in raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if entry.get("type") != "user" or entry.get("isSidechain"):
            continue
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(content, str) and content.strip():
            return content.strip()[:limit]
    return ""


def emit(event, text):
    out = json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})
    sys.stdout.buffer.write(out.encode("utf-8"))


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def git(root, *args):
    try:
        return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                              encoding="utf-8", timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def do_start(root, payload, state):
    state.update(session=payload.get("session_id"), reads=[], warned=0)
    save_state(root, state)
    with open(build(root, "HANDOFF.md"), encoding="utf-8") as fh:
        handoff = fh.read()
    if len(handoff) > 8000:
        handoff = handoff[:8000] + "\n…(truncated — Read the full file)\n"
    parts = ["LOREKEEPER BUILD IS ACTIVE. Current HANDOFF.md follows.\n", handoff]
    snap = build(root, "AUTO-SNAPSHOT.md")
    if mtime(snap) > mtime(build(root, "HANDOFF.md")):
        with open(snap, encoding="utf-8") as fh:
            parts.append("\nAUTO-SNAPSHOT.md (newer than HANDOFF):\n" + fh.read()[:1500])
    parts.append("\nBefore any action, Read docs/build/HANDOFF.md, docs/build/BUILD-PLAN.md and the "
                 "last 150 lines of docs/build/SESSION-LOG.md. Edits are blocked until you do.")
    sys.stdout.buffer.write("".join(parts)[:9800].encode("utf-8"))


def do_post(root, payload, state):
    if state.get("session") != payload.get("session_id"):
        state.update(session=payload.get("session_id"), reads=[], warned=0)
    tool = payload.get("tool_name", "")
    tin = payload.get("tool_input") or {}
    notes = []
    if tool == "Read":
        name = os.path.basename(tin.get("file_path", ""))
        if name in DOCS and os.path.normcase(os.path.dirname(os.path.abspath(tin["file_path"]))) \
                == os.path.normcase(build(root)) and name not in state["reads"]:
            state["reads"].append(name)
    if tool in ("Bash", "PowerShell") and "git commit" in tin.get("command", "") \
            and time.time() - mtime(build(root, "HANDOFF.md")) > 900:
        notes.append("Commit done. If the build position changed, refresh docs/build/HANDOFF.md.")
    tokens = transcript_tokens(payload.get("transcript_path"))
    pct = tokens / window(state)
    if pct < 0.80:
        state["warned"] = 0
    for frac, label, msg in reversed(TIERS):
        if pct < frac:
            continue
        if label == 92 and state.get("warned", 0) >= 92:
            if mtime(build(root, "HANDOFF.md")) < state.get("warn_time", 0):
                notes.append(msg)
        elif state.get("warned", 0) < label:
            state.update(warned=label, warn_time=time.time())
            notes.append(msg)
        break
    save_state(root, state)
    if notes:
        emit("PostToolUse", " ".join(notes) + f" (context ≈{pct:.0%}, {tokens:,} tokens)")


def do_pre(root, payload, state):
    missing = [d for d in DOCS if d not in state.get("reads", [])]
    if state.get("session") != payload.get("session_id"):
        missing = list(DOCS)
    if missing:
        sys.stderr.write("Continuity rule: Read docs/build/" + ", docs/build/".join(missing)
                         + " before editing (after any restart or compaction).\n")
        return 2
    return 0


def do_compact(root, payload, state):
    path = payload.get("transcript_path")
    tokens = transcript_tokens(path)
    win = window(state)
    if tokens and tokens < 0.95 * win:  # compaction came earlier than the tiers assume
        state["window"] = tokens
    stamp = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    age = (time.time() - mtime(build(root, "HANDOFF.md"))) / 60
    with open(build(root, "SESSION-LOG.md"), "a", encoding="utf-8") as fh:
        fh.write(f"\n- compaction {payload.get('trigger', '?')} {stamp} at {tokens:,} tokens "
                 f"({tokens / win:.1%} of {win:,}); HANDOFF age {age:.0f} min\n")
    os.makedirs(build(root, "handoff-history"), exist_ok=True)
    shutil.copy2(build(root, "HANDOFF.md"), build(root, "handoff-history", f"HANDOFF-{stamp}.md"))
    specs = sorted(glob.glob(os.path.join(root, "specs", "[0-9][0-9][0-9]-*")))
    snap = [f"# AUTO-SNAPSHOT {stamp} (written by the PreCompact hook)", "",
            "## git log -5", git(root, "log", "-5", "--oneline"), "",
            "## git status --porcelain", git(root, "status", "--porcelain"), ""]
    if specs:
        snap += [f"## current spec: {os.path.relpath(specs[-1], root)}"]
        try:
            with open(os.path.join(specs[-1], "tasks.md"), encoding="utf-8") as fh:
                snap += [ln.rstrip() for ln in fh if ln.lstrip().startswith("- [ ]")][:5]
        except OSError:
            snap.append("(no tasks.md yet)")
        snap.append("")
    snap += ["## last user message (truncated)", last_user_message(path)]
    with open(build(root, "AUTO-SNAPSHOT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(snap) + "\n")
    state["warned"] = 0
    save_state(root, state)


def main(mode, payload, root=ROOT):
    if not os.path.exists(build(root, "ACTIVE")):
        return 0
    state = load_state(root)
    state.setdefault("reads", [])
    if mode == "pre":
        return do_pre(root, payload, state)
    {"start": do_start, "post": do_post, "compact": do_compact}[mode](root, payload, state)
    return 0


if __name__ == "__main__":
    code = 0
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        code = main(sys.argv[1], data)
    except Exception:  # never break the session over a hook bug
        code = 0
    sys.exit(code)
