"""The progressive story wiki: chapter stamps, story pages, names, reveals and the fact edits."""
import os
import re

from . import fm, store
from .store import LoreError
from .timeinfo import item_dates

STAMP = re.compile(r"[ \t]*\[\s*ch\s*(\d+)\s*(?:[-–]\s*(\d+)\s*)?\]\s*\Z", re.I)
MARK = re.compile(r"\[\s*ch(?![a-z])[^\]\n]*\]", re.I)        # anything shaped like a stamp
CHAPTER = re.compile(r"\s*(?:ch\s*)?(\d+)\s*\Z", re.I)
HEADING = re.compile(r"(#{1,6})[ \t]+(.*?)[ \t#]*\Z")
ITEM = re.compile(r"(?:[-*+]|\d+[.)])(?:[ \t]+|\Z)")          # a top-level list item
LINK = re.compile(r"\[\[([^\[\]|\r\n]+)(?:\|([^\[\]\r\n]*))?\]\]")
SUFFIX = " (story)"
WORKED = {"person": ("Where", "Knows", "Relationships"), "group": ("Relationships",)}


# ---- stamps and chapter numbers -----------------------------------------------------------
def read_stamp(text):
    """'Lost a hand. [ch 4]' -> ('Lost a hand.', 4, None); no stamp -> (text, None, None)."""
    m = STAMP.search(text)
    if not m:
        return text, None, None
    return text[:m.start()].rstrip(), int(m[1]), int(m[2]) if m[2] else None


def stamp_text(start, end=None):
    return f"[ch {start}]" if end is None else f"[ch {start}-{end}]"


def stamp_problems(text):
    """[(code, detail, offset)] for stamp-shaped markers that cannot be used."""
    out, final = [], STAMP.search(text)
    for mark in MARK.finditer(text):
        if final and mark.end() == len(text.rstrip()):
            if final[2] and int(final[2]) < int(final[1]):
                out.append(("STAMP_RANGE", f"{mark[0]} ends before it starts; write [ch {final[1]}-{final[1]}] "
                                           f"or swap the numbers", mark.start()))
        elif STAMP.fullmatch(mark[0]):
            out.append(("STAMP_UNREADABLE", f"{mark[0]} is not at the end of its fact; move it to the end",
                        mark.start()))
        else:
            out.append(("STAMP_UNREADABLE", f"cannot read {mark[0]}; write [ch 7] or [ch 2-5]", mark.start()))
    return out


def chapter(value):
    """'CH003', 'ch 3' or '3' -> 3; anything else -> None."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    m = CHAPTER.match(value) if isinstance(value, str) else None
    return int(m[1]) if m else None


def covers(start, end, n):
    return n is None or ((start is None or start <= n) and (end is None or end >= n))


# ---- facts and sections ---------------------------------------------------------------------
def sections(body, inherit=None):
    """Split a page body into sections of facts. Line indices refer to body.split('\\n')."""
    lines = body.split("\n")
    out = [{"heading": "", "line": None, "facts": []}]
    fact, fence, comment = None, False, False

    def close():
        nonlocal fact
        if fact:
            out[-1]["facts"].append(_fact(lines, *fact, inherit))
            fact = None
    for i, raw in enumerate(lines):
        line = raw.rstrip("\r")
        bare = line.strip()
        if comment:
            comment = "-->" not in line
            continue
        if fence:
            fact[1] = i
            fence = not bare.startswith(("```", "~~~"))
            continue
        heading = None if line[:1] in (" ", "\t") else HEADING.fullmatch(line)
        if not bare or heading or bare.startswith(("<!--", "```", "~~~")) or ITEM.match(line):
            close()
        if heading:
            if len(heading[1]) >= 2:   # the "# Title" line is not a section
                out.append({"heading": heading[2].strip(), "line": i, "facts": []})
        elif bare.startswith("<!--"):
            comment = "-->" not in bare
        elif bare.startswith(("```", "~~~")):
            fact, fence = [i, i, "fence"], True
        elif ITEM.match(line):
            fact = [i, i, "item"]
        elif bare:
            if fact:
                fact[1] = i       # a continuation, nested or lazy line
            else:
                fact = [i, i, "para"]
    close()
    return [s for s in out if s["heading"] or s["facts"]]


def _fact(lines, first, last, kind, inherit):
    raw = [line.rstrip("\r") for line in lines[first:last + 1]]
    if kind == "fence":
        text, start, end = "\n".join(raw), None, None
    else:
        raw[0] = raw[0][ITEM.match(raw[0]).end():] if kind == "item" else raw[0]
        text, start, end = read_stamp("\n".join(line.strip() for line in raw))
    return {"text": text, "from": inherit if start is None else start, "to": end,
            "stamped": start is not None, "first": first, "last": last, "kind": kind}


def plain(text):
    """Link brackets removed: '[[Kresh|the rider]]' -> 'the rider'."""
    return LINK.sub(lambda m: m[2] or m[1], text)


def norm(text):
    return " ".join(plain(text).lower().split())


# ---- the story layer ------------------------------------------------------------------------
class Entry:
    """One wiki entry: an item (or a standalone companion) and the page that holds its stamped facts."""

    def __init__(self, p, item, page):
        self.item, self.page = item, page
        fields = {**(item.fields if item else {}), **(page.fields if page else {})}
        self.type = item.type if item else str(fields.get("type", ""))
        self.name = item.name if item else companion_name(page)
        own = chapter(page.fields.get("first_appearance")) if page else None
        self.appears = own if own is not None else chapter(item.fields.get("first_appearance")) if item else None
        self.parsed = sections(page.body, self.appears) if page else []
        self.offset = page.text[:len(page.text) - len(page.body)].count("\n") if page else 0
        self.names = [(plain(f["text"]), f["from"], f["to"]) for s in self.parsed
                      if s["heading"].lower() == "names" for f in s["facts"] if f["kind"] != "fence"]
        link = store.link_parts(fields.get("revealed_as", ""))
        if link:
            m = STAMP.search(" " + link[1])
            self.reveal = (link[0], int(m[1]) if m else self.appears)
        else:
            self.reveal = None
        self.key = f"path:{item.path if item else page.path}"


def companion_name(page):
    return str(page.fields.get("canonical_name") or page.fields.get("name") or page.stem.removesuffix(SUFFIX))


def folder(p):
    rel = p.config.get("story_wiki")
    return os.path.normpath(os.path.join(p.root, rel)) if rel else None


def story(p):
    """The story layer, built once per project."""
    if "_story" not in p.__dict__:
        p.__dict__["_story"] = Story(p)
    return p.__dict__["_story"]


class Story:
    def __init__(self, p):
        self.p, self.folder = p, folder(p)
        types = p.schema["types"]
        self.narrative = [i for i in p.items if types.get(i.type, {}).get("category") == "narrative"]
        skip = {id(i) for i in self.narrative}
        attached, standalone = {}, []
        for page in self._companions():
            target = store.link_parts(page.fields.get("page", ""))
            item = p.resolve(target[0] if target else companion_name(page))
            if item is not None and id(item) not in attached and id(item) not in skip:
                attached[id(item)] = page
            else:
                standalone.append(page)
        self.entries = [Entry(p, it, attached.get(id(it)) if self.folder else it)
                        for it in p.items if id(it) not in skip]
        self.entries += [Entry(p, None, page) for page in standalone]
        self.by_item = {id(e.item): e for e in self.entries if e.item}
        self.revealed = [e for e in self.entries if e.reveal]
        self.by_path, self.extra = {}, {}
        for e in self.entries:
            for path in (e.item and e.item.path, e.page and e.page.path):
                if path:
                    self.by_path.setdefault(path, e)
            for name in ([] if e.item else [e.name]) + [n for n, _, _ in e.names]:
                self.extra.setdefault(name.lower(), e)
                if e.item:   # names resolve links after names, stems and aliases
                    p.by_alias.setdefault(name.lower(), e.item)
        p._linked = None

    def _companions(self):
        if not self.folder or not os.path.isdir(self.folder):
            return []
        out = []
        for dirpath, dirnames, filenames in os.walk(self.folder):
            dirnames[:] = sorted(d for d in dirnames if d not in store.SKIP_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                if name.endswith(".md") and not name.startswith(("~$", ".")):
                    path = os.path.join(dirpath, name)
                    with open(path, "rb") as fh:
                        data = fh.read()
                    try:
                        front = fm.parse(data.decode("utf-8"))
                    except (UnicodeDecodeError, fm.FrontmatterError):
                        front = None
                    if front is not None and front.fields.get("type"):
                        out.append(store.Item(self.p.rel(path), data.decode("utf-8"), store.sha256(data), front))
        return out

    # ---- lookups and rules ----
    def find(self, ref):
        ref = str(ref).strip()
        if ref.startswith("path:"):
            return self.by_path.get(ref[5:])
        target = fm.link_target(ref) or ref
        item = self.p.by_id.get(target.lower()) or self.p.resolve(target)
        if item is not None and id(item) in self.by_item:
            return self.by_item[id(item)]
        return self.extra.get(target.lower())

    def visible(self, e, n):
        return n is None or e.appears is None or e.appears <= n

    def shown(self, e, n):
        if n is None:
            return e.name
        best = None
        for name, start, end in e.names:
            if covers(start, end, n) and (best is None or (start or -1) >= (best[1] or -1)):
                best = (name, start)
        return best[0] if best else e.name

    def root(self, e, n):
        """The entry e is folded into at chapter n (itself when not revealed yet)."""
        seen = {id(e)}
        while e.reveal and (n is None or e.reveal[1] is None or e.reveal[1] <= n):
            target = self.find(e.reveal[0])
            if target is None or id(target) in seen or not self.visible(target, n):
                break
            seen.add(id(target))
            e = target
        return e

    def folded(self, target, n):
        return [e for e in self.revealed if e is not target and self.visible(e, n) and self.root(e, n) is target]

    def guard(self, text, n):
        """Links to entries hidden at n become plain text; others show the name the reader knows."""
        if n is None:
            return text

        def repl(m):
            name, label = m[1].split("#", 1)[0].strip(), m[2]
            e = self.find(name)
            if e is None:
                return m[0]
            if not self.visible(e, n):
                return label or name
            shown = self.shown(self.root(e, n), n)
            return m[0] if label or shown.lower() == name.lower() else f"[[{name}|{shown}]]"
        return LINK.sub(repl, text)

    def label(self, type_):
        spec = self.p.schema["types"].get(type_, {})
        return spec.get("plural") or spec.get("label") or type_ or "Other"

    def chapters(self):
        used = {e.appears for e in self.entries}
        for e in self.entries:
            used.update(x for s in e.parsed for f in s["facts"] for x in (f["from"], f["to"]))
            used.update(x for _, a, b in e.names for x in (a, b))
            used.add(e.reveal[1] if e.reveal else None)
        used.update(chapter(i.fields.get("first_appearance")) for i in self.p.items)
        used.discard(None)
        if not used:
            return []
        labels = {}
        for it in sorted(self.narrative, key=lambda i: not i.path.endswith(".md")):   # real pages before cards
            number = narrative_number(it)
            if number is not None:
                labels.setdefault(number, str(it.fields.get("title") or it.name))
        return [{"n": k, "name": labels.get(k)} for k in range(0 if 0 in used else 1, max(used) + 1)]

    # ---- the two views ----
    def index(self, n):
        groups = {}
        for e in self.entries:
            if self.visible(e, n) and self.root(e, n) is e:
                also = [self.shown(f, n) for f in self.folded(e, n)]
                groups.setdefault(e.type, []).append(
                    {"name": self.shown(e, n), "type": e.type, "key": e.key, "page": e.item.path if e.item else None,
                     "appears": e.appears, "also": also})
        out = [{"type": t, "label": self.label(t), "count": len(rows),
                "entries": sorted(rows, key=lambda r: r["name"].casefold())}
               for t, rows in groups.items()]
        out.sort(key=lambda g: g["label"].casefold())
        return {"mode": mode(n), "as_of": n, "groups": out, "count": sum(g["count"] for g in out),
                "chapters": self.chapters()}

    def card(self, ref, n):
        e = self.find(ref)
        if e is None or not self.visible(e, n):
            at = "" if n is None else f" as of chapter {n}"
            raise LoreError("NOT_FOUND", f"no wiki entry named {ref!r}{at}; list entries with: lore wiki"
                            + ("" if n is None else f" --as-of {n}"))
        r = self.root(e, n)
        out = []

        def take(entry, tag):
            for s in entry.parsed:
                if s["heading"].lower() == "names":
                    continue
                shown = [self._fact(f, n, tag) for f in s["facts"] if covers(f["from"], f["to"], n)]
                if tag and not shown:
                    continue
                into = next((o for o in out if o["heading"].lower() == s["heading"].lower()), None)
                if into is None:
                    into = {"heading": s["heading"], "facts": []}
                    out.append(into)
                into["facts"] += shown
        take(r, None)
        folded = self.folded(r, n)
        for f in folded:
            take(f, self.shown(f, n))
        self._worked_out(r, n, out)
        names = [{"name": name, "from": a, "to": b} for name, a, b in r.names
                 if n is None or (covers(a, b, n) and name != self.shown(r, n))]
        card = {"mode": mode(n), "as_of": n, "key": r.key, "name": self.shown(r, n), "type": r.type,
                "page": r.item.path if r.item else None, "story_page": r.page.path if r.page else None,
                "version": r.page.version if r.page else None, "appears": r.appears, "names": names,
                "also": [self.shown(f, n) for f in folded], "sections": out}
        if e is not r:
            card["opened"] = self.shown(e, n)
        if n is None:
            card["fields"] = (r.item or r.page).fields
            if self.folder and r.item:
                card["body"] = r.item.body
        card["chapters"] = self.chapters()
        return card

    def _fact(self, f, n, tag):
        out = {"text": self.guard(f["text"], n), "from": f["from"], "to": f["to"]}
        if tag:
            out["as"] = tag
        return out

    def _worked_out(self, r, n, out):
        p = self.p
        category = p.schema["types"].get(r.type, {}).get("category")
        if r.item is None or category not in WORKED:
            return
        seen = lambda it: it is not None and id(it) in self.by_item and self.visible(self.by_item[id(it)], n)
        events = sorted(((item_dates(p, ev)[0], ev) for ev in p.backlinks(r.item).get("participants", [])
                         if seen(ev)), key=lambda pair: (pair[0].lo, pair[0].hi) if pair[0] else (float("inf"),) * 2)
        made = {"Where": [], "Knows": [], "Relationships": []}
        placed = [(ev, o) for start, ev in events if start
                  for o in [next((o for _, o, _ in p.links(ev).get("location", []) if o), None)] if seen(o)]
        if placed:
            made["Where"].append(f"[[{placed[-1][1].name}]] ({placed[-1][0].name})")
        known = {}
        for _, ev in events:
            for _, o, _ in p.links(ev).get("learns", []):
                if seen(o):
                    known.setdefault(o.name, f"[[{o.name}]] ({ev.name})")
        made["Knows"] = list(known.values())
        roles, kinds = p.schema["roles"], ("person", "group")

        def related(it, other, lag):
            if not seen(other) or p.schema["types"].get(other.type, {}).get("category") not in kinds:
                return False
            m = STAMP.search(" " + (lag or ""))
            return covers(int(m[1]) if m else self.by_item[id(it)].appears, None, n)
        for role, links in p.links(r.item).items():
            for _, o, lag in links:
                if role != "revealed_as" and related(r.item, o, lag):
                    made["Relationships"].append(f"{roles.get(role, {}).get('label') or role}: [[{o.name}]]")
        for role, sources in p.backlinks(r.item).items():
            for src in sources:
                lag = next((lag for _, o, lag in p.links(src).get(role, []) if o is r.item), "")
                if role != "revealed_as" and related(src, src, lag):
                    inverse = roles.get(role, {}).get("inverse") or f"{role} (from)"
                    made["Relationships"].append(f"{inverse}: [[{src.name}]]")
        for heading in WORKED[category]:
            into = next((o for o in out if o["heading"].lower() == heading.lower()), None)
            if (into and into["facts"]) or not made[heading]:
                continue
            if into is None:
                into = {"heading": heading, "facts": []}
                out.append(into)
            into["facts"] += [{"text": self.guard(t, n), "from": None, "to": None, "worked_out": True}
                              for t in dict.fromkeys(made[heading])]

    def findings(self):
        out = []
        for e in self.entries:
            if e.page is None:
                continue
            lines = e.page.body.split("\n")
            for s in e.parsed:
                for f in s["facts"]:
                    if f["kind"] == "fence":
                        continue
                    raw = "\n".join(line.rstrip("\r") for line in lines[f["first"]:f["last"] + 1])
                    for code, detail, at in stamp_problems(raw):
                        line = e.offset + f["first"] + 1 + raw[:at].count("\n")
                        out.append(store.finding("WARN", code, detail, e.page.path, line))
        return out


def mode(n):
    return "complete" if n is None else "progressive"


def narrative_number(it):
    for key in ("order", "chapter"):
        if chapter(it.fields.get(key)) is not None:
            return chapter(it.fields.get(key))
    m = re.search(r"\d+", it.id) or re.search(r"\d+", it.name)
    return int(m[0]) if m else None


# ---- fact edits -----------------------------------------------------------------------------
def _check_section(section):
    section = section.strip().lstrip("#").strip() if isinstance(section, str) else ""
    if not section or "\n" in section or "\r" in section:
        raise LoreError("INVALID", "section must be a heading name on one line, e.g. Beliefs")
    return section


def _check_text(text):
    text = text.strip() if isinstance(text, str) else ""
    text = text[2:].strip() if text.startswith("- ") else text
    if not text:
        raise LoreError("INVALID", "text is empty; write the fact as one sentence")
    if "\n" in text or "\r" in text:
        raise LoreError("INVALID", "text must be one line; add each fact separately")
    if MARK.search(text):
        raise LoreError("INVALID", "leave the [ch …] marker out of text; give the chapters with from and to")
    if text.startswith("#"):
        raise LoreError("INVALID", "text cannot start with #; that would make a heading")
    return text


def _check_span(start, end):
    if start < 0:
        raise LoreError("INVALID", "from must be a chapter number, 0 or more")
    if end is not None and end < start:
        raise LoreError("INVALID", f"to ({end}) is before from ({start}); a fact ends after it starts")


def companion_path(p, s, type_, name):
    spec = p.schema["types"].get(type_, {})
    sub = spec.get("folder") or spec.get("plural") or type_
    stem = store.DEVICE.sub(r"\1_", store.BAD_FILENAME.sub("-", name).strip(" ."))
    path = os.path.normpath(os.path.join(s.folder, sub, stem + SUFFIX + ".md"))
    if not store.inside(s.folder, path):
        raise LoreError("INVALID", f"type {type_!r} folder points outside the story wiki folder")
    return path


def starter(p, type_, name):
    heads = p.schema["types"].get(type_, {}).get("sections") or []
    return f"\n# {name}\n\n" + "".join(f"## {h}\n\n" for h in heads)


def _open(p, s, ref, version, need):
    """(entry, path, text, sha) of an entry's story page; text is None when the page must be created."""
    e = s.find(ref)
    if e is None or e.page is None and need:
        if e is None:
            raise LoreError("NOT_FOUND", f"no wiki entry named {ref!r}; list entries with: lore wiki")
        raise LoreError("NOT_FOUND", f"{e.name} has no story facts yet; add one with fact-add")
    if e.page is None:
        return e, companion_path(p, s, e.type, e.name), None, None
    path = os.path.join(p.root, e.page.path)
    with open(path, "rb") as fh:
        data = fh.read()
    sha = store.sha256(data)
    if version is not None and version != sha:
        raise LoreError("CONFLICT", f"{e.page.path} changed since it was read; read it again (lore wiki "
                        f"{e.name!r}) and retry", {"version": sha, "path": e.page.path})
    return e, path, data.decode("utf-8"), sha


def _split(text):
    front = fm.parse(text)
    body = front.body if front else text
    return text[:len(text) - len(body)], body.split("\n"), "\r" if "\r\n" in text else ""


def _find_section(lines, section, inherit=None):
    return next((s for s in sections("\n".join(lines), inherit) if s["heading"].lower() == section.lower()), None)


def _section(lines, section, e):
    found = _find_section(lines, section, e.appears)
    if found is None:
        heads = [s["heading"] for s in sections("\n".join(lines)) if s["heading"]]
        raise LoreError("NOT_FOUND", f"{e.name} has no section {section!r}; sections: {', '.join(heads) or 'none'}")
    return found


def _match(found, fact, e, section):
    want = norm(fact)
    hit = next((f for f in found["facts"] if want and norm(f["text"]).startswith(want)), None)
    if hit is None:
        starts = "; ".join(plain(f["text"])[:40] for f in found["facts"][:6]) or "none"
        raise LoreError("NOT_FOUND", f"no fact in {e.name} › {section} starts with {fact!r}; facts: {starts}")
    return hit


def _write(p, path, text, sha):
    version = store.atomic_write(path, text, expect=sha, create=sha is None)
    p.__dict__.pop("_story", None)
    return version


def fact_add(p, item, section, text, start, end=None, version=None, type_=None):
    section, text = _check_section(section), _check_text(text)
    _check_span(start, end)
    s = story(p)
    if s.find(item) is None:
        if not s.folder:
            raise LoreError("NOT_FOUND", f"no item named {item!r}; create it first (lore create TYPE {item!r}), "
                                         "then add facts")
        if not type_:
            raise LoreError("NOT_FOUND", f"no item or story page named {item!r}; pass --type (e.g. character) to "
                                         "start a story page for someone who has no page yet")
        if type_ not in p.schema["types"]:
            raise LoreError("INVALID", f"unknown type {type_!r}; types: {', '.join(p.schema['types'])}")
        name = p.check_name(item)
        e, path, sha = None, companion_path(p, s, type_, name), None
        page = fm.update("", set={"type": type_, "canonical_name": name, "first_appearance": str(start)},
                         body=starter(p, type_, name))
    else:
        e, path, page, sha = _open(p, s, item, version, need=False)
        name = e.name
        if page is None:
            page = fm.update("", set={"type": e.type, "page": f"[[{e.item.name}]]"}, body=starter(p, e.type, name))
    created = sha is None
    if created and version is not None:
        raise LoreError("CONFLICT", f"{name} has no story page yet; send no version to create it", {"version": None})
    head, lines, cr = _split(page)
    line = f"- {text} {stamp_text(start, end)}{cr}"
    found = _find_section(lines, section)
    if found is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [cr, f"## {section}{cr}", cr, line, ""]
    else:
        last = found["facts"][-1]["last"] if found["facts"] else None
        if last is None:
            lines[found["line"] + 1:found["line"] + 1] = [cr, line]
        else:
            lines[last + 1:last + 1] = [line]
    new = _write(p, path, head + "\n".join(lines), sha)
    return {"item": name, "path": p.rel(path), "version": new, "created": created, "section": section,
            "text": text, "from": start, "to": end}


def fact_end(p, item, section, fact, after=None, reopen=False, version=None):
    if not reopen and after is None:
        raise LoreError("INVALID", "give after (the last chapter the fact is true in), or reopen to make it "
                                   "current again")
    s = story(p)
    e, path, page, sha = _open(p, s, item, version, need=True)
    section = _check_section(section)
    head, lines, cr = _split(page)
    hit = _match(_section(lines, section, e), fact, e, section)
    start = hit["from"] if hit["from"] is not None else 1
    end = None if reopen else after
    if end is not None and end < start:
        raise LoreError("INVALID", f"after ({end}) is before the fact starts (chapter {start})")
    last = lines[hit["last"]].rstrip("\r")
    m = STAMP.search(last)
    lines[hit["last"]] = f"{last[:m.start()] if m else last.rstrip()} {stamp_text(start, end)}{cr}"
    new = _write(p, path, head + "\n".join(lines), sha)
    return {"item": e.name, "path": e.page.path, "version": new, "section": section, "text": hit["text"],
            "from": start, "to": end}


def fact_remove(p, item, section, fact, version=None):
    s = story(p)
    e, path, page, sha = _open(p, s, item, version, need=True)
    section = _check_section(section)
    head, lines, _ = _split(page)
    hit = _match(_section(lines, section, e), fact, e, section)
    del lines[hit["first"]:hit["last"] + 1]
    new = _write(p, path, head + "\n".join(lines), sha)
    return {"item": e.name, "path": e.page.path, "version": new, "section": section, "removed": hit["text"]}
