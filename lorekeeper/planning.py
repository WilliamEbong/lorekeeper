"""The planning wiki: the author's designed end state as per-entity pages whose facts cite their
source documents, link lists Lorekeeper computes, an impact search, and the recorded planning change."""
import collections
import datetime
import difflib
import os
import re

from . import fm, store, wiki
from .store import LoreError

ROLES = ("dialogues", "chapters", "ideas", "overrides", "prose")
SOURCE_KEYS = {"name", "file", "skip", *ROLES}
SUFFIX = " (plan)"
IDEAS = "ideas"
CITE = re.compile(r"[ \t]*\[\s*src\s*:\s*([^\]\n]*)\]\s*\Z", re.I)
CITE_ANY = re.compile(r"\[\s*src\s*:", re.I)
# a heading's section number: 23, 0.8.4, A.252, B.2A, HO-031 (a leading § is ignored)
NUMBER = re.compile(r"§?\s*(\d\w*(?:\.\w+)*|[A-Za-z]{1,4}\.\d\w*(?:\.\w+)*|[A-Za-z]{1,4}-\d+)(?=\Z|[\s.:)—–-])")
ID_LINE = re.compile(r"\s*\*\*ID:\*\*\s*`?([A-Za-z]{1,4}-\d+)`?")   # an override register entry
SPEAKER = re.compile(r"\s*\*\*([^*:\n]+?)(?:\s*\([^)\n]*\))?:\*\*")
POSITION = re.compile(r"(?<![*\w])\*([^*\n]{1,60}?)\*\s*[—–-]")   # "*Selena* — the distinction is legal…"
CHAPTER_HEAD = re.compile(r"(?:chapter|ch)\.?\s*0*(\d+)\b\s*[:.—–-]?\s*(.*)", re.I)
MEMBER_ROLES = ("kind", "member_of")


def norm(text):
    return " ".join(re.sub(r"[\W_]+", " ", str(text).lower()).split())


def read_citation(text):
    """'Born in 1782. [src: A §1; B 2]' -> ('Born in 1782.', ['A §1', 'B 2'])."""
    m = CITE.search(text)
    if not m:
        return text, []
    return text[:m.start()].rstrip(), [r.strip() for r in m[1].split(";") if r.strip()]


def cite(text, refs):
    return f"{text} [src: {'; '.join(refs)}]" if refs else text


# ---- source documents ------------------------------------------------------------------------
class Source:
    """One planning document, read once and split into sections by its headings."""

    def __init__(self, name, path, rank, role, skip=()):
        self.name, self.path, self.rank, self.role, self.skip = name, path, rank, role, tuple(skip)
        self._lines = None

    def lines(self):
        if self._lines is None:
            if not os.path.isfile(self.path):
                raise LoreError("NOT_FOUND", f"source {self.name!r} file not found: {self.path}; update "
                                             "planning_wiki.sources in the settings file")
            with open(self.path, "rb") as fh:
                data = fh.read()
            try:
                self.raw = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise LoreError("INVALID", f"source {self.name!r} is not UTF-8 text: {self.path}") from exc
            self.version = store.sha256(data)
            self._lines = self.raw.split("\n")
            self._sections = self._parse()
        return self._lines

    def _parse(self):
        # ponytail: code fences are not tracked; planning documents use bare ``` lines as separators, unbalanced,
        # and the sagas' own card parser reads headings the same way. Track fences if a world needs it.
        out, example = [], False
        for i, raw in enumerate(self._lines):
            line = raw.rstrip("\r")
            m = wiki.HEADING.fullmatch(line) if line[:1] == "#" else None
            if m:
                title = m[2].strip()
                num = NUMBER.match(title)
                number = num[1] if num and any(c.isdigit() for c in num[1]) else None
                bare = title[num.end():].lstrip(" .:)—–-") if number else title
                example = "example" in title.lower()   # a register's illustration, not an entry
                out.append({"level": len(m[1]), "title": title, "number": number, "bare": bare, "line": i,
                            "example": example})
            elif self.role == "overrides" and ID_LINE.match(line) and not (
                    out and out[-1]["level"] <= 6 and out[-1]["number"] == ID_LINE.match(line)[1]):
                # (an entry written as "## HO-104 — title" already has its section; its **ID:** line adds none)
                ident = ID_LINE.match(line)[1]
                out.append({"level": 7, "title": ident, "number": ident, "bare": ident, "line": i,
                            "example": "example" in line.lower()})   # real entries may follow an example block
        for k, s in enumerate(out):
            s["end"] = next((t["line"] for t in out[k + 1:] if t["level"] <= s["level"]), len(self._lines))
            s["ref"] = s["number"] or s["title"]
        return out

    def sections(self):
        self.lines()
        return self._sections

    def outline(self):
        lines = self.lines()
        return [{"ref": s["ref"], "title": s["title"], "level": s["level"], "line": s["line"] + 1,
                 "end": s["end"], "bytes": sum(len(x.encode("utf-8")) + 1 for x in lines[s["line"]:s["end"]])}
                for s in self.sections()]

    def find(self, ref):
        want = str(ref).strip()
        want = want[1:].strip() if want.startswith("§") else want
        if not want:
            raise LoreError("INVALID", f"give a section of {self.name}: a number such as 23.4 or a heading's "
                                       f"title; list them with: lore planning-source {self.name!r}")
        secs = self.sections()
        num = NUMBER.match(want)
        if num and any(c.isdigit() for c in num[1]):   # a number, optionally followed by the start of the title
            rest = norm(want[num.end():])
            hits = [s for s in secs if s["number"] and s["number"].lower() == num[1].lower()
                    and norm(s["bare"]).startswith(rest)]
        else:
            n = norm(want)
            hits = [s for s in secs if n in (norm(s["title"]), norm(s["bare"]))] or \
                [s for s in secs if n and (norm(s["title"]).startswith(n) or norm(s["bare"]).startswith(n))]
        if len(hits) > 1:
            some = "; ".join(s["title"] for s in hits[:8])
            raise LoreError("INVALID", f"{ref!r} matches several sections of {self.name}: {some}; give the number "
                                       f"and the start of the title, e.g. §{hits[1]['ref']} {hits[1]['bare'][:20]}")
        if not hits:
            close = difflib.get_close_matches(want, [s["title"] for s in secs] + [s["ref"] for s in secs], 6, 0.6)
            raise LoreError("NOT_FOUND", f"no section {ref!r} in {self.name}"
                            + (f"; close: {'; '.join(close)}" if close else "")
                            + f"; list its sections with: lore planning-source {self.name!r}")
        return hits[0]

    def text(self, sec):
        return "\n".join(x.rstrip("\r") for x in self.lines()[sec["line"]:sec["end"]]).rstrip()

    def at(self, i):
        """The innermost section holding line i, or None before the first heading."""
        best = None
        for s in self.sections():
            if s["line"] > i:
                break
            if i < s["end"]:
                best = s
        return best

    def entries(self):
        """A register's real entries (sections whose ref is an id such as HO-031), examples left out."""
        return [s for s in self.sections() if not s["example"] and re.fullmatch(r"[A-Za-z]+-\d+", s["number"] or "")]

    def next_id(self):
        ids = [s["number"].upper().split("-") for s in self.entries()]
        if not ids:
            return "HO-001"
        prefix = collections.Counter(p for p, _ in ids).most_common(1)[0][0]   # the register's own series
        return f"{prefix}-{max(int(n) for p, n in ids if p == prefix) + 1:03d}"


# ---- settings, pages and entries -------------------------------------------------------------
def _settings(cfg):
    def bad(message):
        raise LoreError("INVALID", message)
    if not isinstance(cfg, dict):
        bad("planning_wiki must be an object with folder and sources")
    for key in set(cfg) - {"folder", "sources", "exclude_names"}:
        bad(f"unknown key {key!r} in planning_wiki; its keys are folder, sources and exclude_names")
    if not isinstance(cfg.get("folder"), str) or not cfg["folder"].strip():
        bad('planning_wiki needs folder: where planning pages live, e.g. "../Planning Wiki"')
    sources = cfg.get("sources", [])
    if not isinstance(sources, list):
        bad("planning_wiki.sources must be a list of {name, file} objects, highest authority first")
    names = set()
    for i, s in enumerate(sources):
        where = f"planning_wiki.sources[{i}]"
        if not isinstance(s, dict):
            bad(f"{where} must be an object with name and file")
        for key in set(s) - SOURCE_KEYS:
            bad(f"unknown key {key!r} in {where}; keys: name, file, skip, {', '.join(ROLES)}")
        if not all(isinstance(s.get(k), str) and s[k].strip() for k in ("name", "file")):
            bad(f"{where} needs name and file")
        if s["name"].lower() in names:
            bad(f"{where}: two sources are named {s['name']!r}; citations need unique names")
        names.add(s["name"].lower())
        if sum(bool(s.get(r)) for r in ROLES) > 1:
            bad(f"{where} ({s['name']}) takes at most one of {', '.join(ROLES)}")
        if s.get("prose"):
            try:
                ok = s["file"].format(n=1) != s["file"]
            except (KeyError, IndexError, ValueError):
                ok = False
            if not ok:
                bad(f"{where} ({s['name']}): a prose file is a pattern with {{n}} and no other braces, "
                    "e.g. ../Chapters/CH{n:03d}/CHAPTER.md")
        if not isinstance(s.get("skip", []), list) or not all(isinstance(x, str) for x in s.get("skip", [])):
            bad(f"{where}.skip must be a list of line starts, e.g. [\"Meanwhile:\"]")
    if sum(bool(s.get("overrides")) for s in sources) > 1:
        bad("planning_wiki: only one source may be the overrides register")
    exclude = cfg.get("exclude_names", [])
    if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
        bad("planning_wiki.exclude_names must be a list of names")
    return cfg


def plan(p):
    """The planning layer, built once per project."""
    if "_plan" not in p.__dict__:
        p.__dict__["_plan"] = Plan(p)
    return p.__dict__["_plan"]


def folder_of(config):
    cfg = config.get("planning_wiki")
    return cfg.get("folder") if isinstance(cfg, dict) and isinstance(cfg.get("folder"), str) else None


class Entry:
    def __init__(self, page, item):
        self.page, self.item = page, item
        f = page.fields
        self.type = str(f.get("type", ""))
        self.name = str(f.get("canonical_name") or f.get("name") or (item.name if item else "")
                        or page.stem.removesuffix(SUFFIX))
        aliases = f.get("aliases", [])
        aliases = aliases if isinstance(aliases, list) else [aliases] if aliases else []
        self.names = list(dict.fromkeys([self.name] + [str(a) for a in aliases]
                                        + ([item.name] + item.aliases if item else [])))
        self.key = "plan:" + store.sha256(page.path.encode("utf-8"))[:12]
        self.offset = page.text[:len(page.text) - len(page.body)].count("\n")
        self.parsed = parse(page.body)

        def tags(fields):
            t = fields.get("tags", [])
            return set(t if isinstance(t, list) else [t] if t else [])
        self.tags = tags(f) | (tags(item.fields) if item else set())
        mt = f.get("member_tags", [])
        self.member_tags = set(mt if isinstance(mt, list) else [mt] if mt else [])

    def decided(self):
        return [(s, x) for s in self.parsed if s["heading"].lower() != IDEAS for x in s["facts"]]

    def ideas(self):
        return [(s, x) for s in self.parsed if s["heading"].lower() == IDEAS for x in s["facts"]]


def parse(body):
    """Sections and facts with each fact's citation split off; ids ignore citations."""
    parsed = wiki.sections(body)
    for s in parsed:
        for f in s["facts"]:
            f["text"], f["refs"] = (f["text"], []) if f["kind"] == "fence" else read_citation(f["text"])
    return wiki.number(parsed)


class Matcher:
    """Whole-word, case-sensitive search for entries' names; short and excluded names never match."""

    def __init__(self, entries, exclude):
        self.names = {}
        for e in entries:
            for n in e.names:
                n = n.strip()
                if len(re.sub(r"\W", "", n)) >= 3 and n.lower() not in exclude:
                    self.names.setdefault(n, []).append(e)
        ordered = sorted(self.names, key=len, reverse=True)
        pattern = r"(?<!\w)(" + "|".join(map(re.escape, ordered)) + r")(?!\w)"
        self.rx = re.compile(pattern) if ordered else None
        self.rx_any_case = re.compile(pattern, re.I) if ordered else None   # for headings, often in capitals
        self.lower = {}
        for n, es in self.names.items():
            self.lower.setdefault(n.lower(), []).extend(es)

    def find(self, text, any_case=False):
        out = {}
        rx = self.rx_any_case if any_case else self.rx
        for m in rx.finditer(text) if rx else ():
            for e in (self.lower[m[1].lower()] if any_case else self.names[m[1]]):
                out.setdefault(id(e), e)
        return list(out.values())


class Plan:
    def __init__(self, p):
        cfg = p.config.get("planning_wiki")
        if not cfg:
            raise LoreError("NOT_FOUND", "this world has no planning wiki: add a planning_wiki setting with folder and "
                                       "sources to the settings file (see the user guide, 'The planning wiki')")
        _settings(cfg)
        self.p = p
        self.folder = os.path.normpath(os.path.join(p.root, cfg["folder"]))
        here, root = (os.path.normcase(os.path.realpath(x)) for x in (self.folder, p.root))
        if here == root or root.startswith(here.rstrip(os.sep) + os.sep):
            raise LoreError("INVALID", "planning_wiki.folder must not be the project folder or contain it, or every "
                                       "page would count as a planning page; use a folder of its own, e.g. "
                                       "\"../Planning Wiki\"")
        story = wiki.folder(p)
        if story:
            story = os.path.normcase(os.path.realpath(story))
            if here == story or here.startswith(story + os.sep) or story.startswith(here + os.sep):
                raise LoreError("INVALID", "planning_wiki.folder must not overlap the story_wiki folder; give each "
                                           "layer a folder of its own")
        self.sources = []
        for rank, s in enumerate(cfg.get("sources", []), 1):
            src = Source(s["name"], os.path.normpath(os.path.join(p.root, s["file"])), rank,
                         next((r for r in ROLES if s.get(r)), None), s.get("skip", []))
            src.pattern = s["file"]   # a prose source's chapter files: pattern.format(n=...) under the project root
            self.sources.append(src)
        self.exclude = {n.lower() for n in cfg.get("exclude_names", [])}
        self.problems = []
        self.entries = []
        by_item = {}
        for page in self._pages():
            target = store.link_parts(page.fields.get("page", ""))
            name = str(page.fields.get("canonical_name") or page.fields.get("name") or page.stem.removesuffix(SUFFIX))
            item = p.resolve(target[0] if target else name)
            if item is not None and id(item) in by_item:
                item = None   # one planning page per item
            e = Entry(page, item)
            if item is not None:
                by_item[id(item)] = e
            self.entries.append(e)
        self.by_item = by_item
        self.by_key = {e.key: e for e in self.entries}
        self.by_name = {}
        for e in self.entries:   # canonical names first: an alias never hides another entry's own name
            self.by_name.setdefault(e.name.lower(), e)
        for e in self.entries:
            for n in e.names:
                self.by_name.setdefault(n.lower(), e)
        self._links = None

    def _pages(self):
        out = []
        if not os.path.isdir(self.folder):
            return out
        for dirpath, dirnames, filenames in os.walk(self.folder):
            dirnames[:] = sorted(d for d in dirnames if d not in store.SKIP_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                if not name.endswith(".md") or name.startswith(("~$", ".")) or name.lower() == "readme.md":
                    continue
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    data = fh.read()
                try:
                    front = fm.parse(data.decode("utf-8"))
                except (UnicodeDecodeError, fm.FrontmatterError):
                    front = None
                if front is not None and front.fields.get("type"):
                    out.append(store.Item(self.p.rel(path), data.decode("utf-8"), store.sha256(data), front))
                else:
                    self.problems.append(store.finding("WARN", "PLAN_PAGE_UNREADABLE", "not used: a planning page "
                                                       "needs UTF-8 text and frontmatter with type:", self.p.rel(path)))
        return out

    # ---- lookups ----
    def find(self, ref):
        ref = str(ref).strip()
        if ref.startswith("plan:"):
            return self.by_key.get(ref)
        target = (fm.link_target(ref) or ref).strip()
        e = self.by_name.get(target.lower())
        if e is None:
            item = self.p.resolve(target)
            e = self.by_item.get(id(item)) if item is not None else None
        return e

    def get(self, ref):
        e = self.find(ref)
        if e is None:
            raise LoreError("NOT_FOUND", f"no planning entry named {ref!r}; list entries with: lore planning")
        return e

    def source(self, name):
        s = next((s for s in self.sources if s.name.lower() == str(name).strip().lower()), None)
        if s is None:
            raise LoreError("NOT_FOUND", f"no planning source named {name!r}; sources: "
                                         f"{', '.join(s.name for s in self.sources) or 'none'}")
        return s

    def resolve(self, ref):
        """'World Bible §23.4' -> {ref, source, section, title, rank, role, found, line}."""
        ref = ref.strip()
        out = {"ref": ref, "source": None, "section": None, "title": None, "rank": None, "role": None, "found": False}
        for s in sorted(self.sources, key=lambda s: -len(s.name)):
            n = len(s.name)
            if ref.lower().startswith(s.name.lower()) and (len(ref) == n or not ref[n].isalnum()):
                section = ref[n:].strip()
                section = section[1:].strip() if section.startswith("§") else section
                out.update(source=s.name, section=section, rank=s.rank, role=s.role)
                if s.role != "prose":
                    try:
                        sec = s.find(section)
                        out.update(title=sec["title"], found=True, line=sec["line"] + 1)
                    except LoreError:
                        pass
                return out
        return out

    def matcher(self):
        if "_matcher" not in self.__dict__:
            self._matcher = Matcher(self.entries, self.exclude)
        return self._matcher

    # ---- computed link lists ----
    def links(self):
        if self._links is not None:
            return self._links
        m = self.matcher()
        out = {id(e): {"members": {}, "dialogues": [], "appears_in": {}, "ideas": []} for e in self.entries}
        for e in self.entries:   # members: kind and member_of links, and member_tags
            fields = [e.page.fields] + ([e.item.fields] if e.item else [])
            for f in fields:
                for role in MEMBER_ROLES:
                    values = f.get(role, [])
                    for value in values if isinstance(values, list) else [values]:
                        parts = store.link_parts(value) if value else None
                        k = self.find(parts[0]) if parts else None
                        if k is not None and k is not e:
                            out[id(k)]["members"][id(e)] = e
            for k in self.entries:
                if k is not e and k.member_tags & e.tags:
                    out[id(k)]["members"][id(e)] = e
        for s in self.sources:
            if s.role not in ("dialogues", "chapters", "ideas") or not os.path.isfile(s.path):
                continue
            lines, secs = s.lines(), [x for x in s.sections() if x["level"] <= 6]
            if s.role == "dialogues":
                # entries are the deepest numbered headings (§A.252 …); a deeper unnumbered "#### Beats" stays inside
                deepest = max((x["level"] for x in secs if x["number"]), default=None) or \
                    max((x["level"] for x in secs), default=0)
                numbered = any(x["number"] for x in secs)
                for x in secs:
                    if x["level"] != deepest or (numbered and not x["number"]):   # "The tic list" is no dialogue
                        continue
                    # the entry's own heading and the headings around it ("PART A — SELENA VANE AND ILYRA"),
                    # then its speakers: "**Name:**" labels and "*Name* —" position markers
                    around = [y["title"] for y in secs if y["line"] < x["line"] and y["end"] >= x["end"]]
                    named = m.find("\n".join(around + [x["title"]]), any_case=True)
                    for raw in lines[x["line"] + 1:x["end"]]:
                        label = SPEAKER.match(raw)
                        if label:
                            named += m.find(label[1])
                        for who in POSITION.findall(raw):
                            named += m.find(who)
                    for e in dict.fromkeys(named):
                        row = {"source": s.name, "section": x["ref"], "title": x["title"]}
                        if row not in out[id(e)]["dialogues"]:
                            out[id(e)]["dialogues"].append(row)
            elif s.role == "chapters":
                for n, title, text, ref in self._cards(s):
                    for e in m.find(text):
                        out[id(e)]["appears_in"].setdefault(n, {"n": n, "title": title, "source": s.name,
                                                                "section": ref})
            else:
                for x in secs:
                    for e in m.find(x["title"]):
                        out[id(e)]["ideas"].append({"source": s.name, "section": x["ref"], "title": x["title"],
                                                    "idea": True})
        types = self.p.schema["types"]
        for it in self.p.items:   # a world's own chapter pages
            if types.get(it.type, {}).get("category") == "narrative":
                n = wiki.narrative_number(it)
                if n is not None:
                    for e in m.find(f"{it.name}\n{it.body}"):
                        out[id(e)]["appears_in"].setdefault(n, {"n": n, "title": str(it.fields.get("title") or it.name),
                                                                "source": None})
        self._links = out
        return out

    def _cards(self, s):
        """(chapter number, title, card text, section ref) for each 'Chapter N' heading of a chapters source."""
        lines, secs = s.lines(), [x for x in s.sections() if x["level"] <= 6]
        for k, x in enumerate(secs):
            m = CHAPTER_HEAD.fullmatch(x["title"])
            if not m:
                continue
            stop = secs[k + 1]["line"] if k + 1 < len(secs) else len(lines)
            body = [raw.rstrip("\r") for raw in lines[x["line"]:stop]]
            body = [b for b in body if not any(b.lstrip(" *-_>").lower().startswith(p.lower()) for p in s.skip)]
            yield int(m[1]), m[2].strip(), "\n".join(body), x["ref"]

    # ---- views ----
    def label(self, type_):
        spec = self.p.schema["types"].get(type_, {})
        return spec.get("plural") or spec.get("label") or type_[:1].upper() + type_[1:] or "Other"

    def index(self):
        groups = {}
        for e in self.entries:
            groups.setdefault(e.type, []).append({
                "name": e.name, "type": e.type, "key": e.key, "page": e.item.name if e.item else None,
                "facts": len(e.decided()), "ideas": len(e.ideas())})
        out = [{"type": t, "label": self.label(t), "count": len(rows),
                "entries": sorted(rows, key=lambda r: r["name"].casefold())} for t, rows in groups.items()]
        out.sort(key=lambda g: g["label"].casefold())
        return {"mode": "planning", "groups": out, "count": len(self.entries), "problems": self.findings(),
                "sources": [{"name": s.name, "role": s.role, "rank": s.rank, "found": s.role == "prose"
                             or os.path.isfile(s.path)} for s in self.sources]}

    def _fact(self, f, idea=False):
        out = {"id": f["id"], "text": f["text"], "sources": [self.resolve(r) for r in f["refs"]]}
        if idea:
            out["idea"] = True
        return out

    def card(self, ref):
        e = self.get(ref)
        links = self.links()[id(e)]
        sections = [{"heading": s["heading"], "facts": [self._fact(f) for f in s["facts"]]}
                    for s in e.parsed if s["heading"].lower() != IDEAS]
        return {"mode": "planning", "key": e.key, "name": e.name, "type": e.type, "path": e.page.path,
                "version": e.page.version, "page": e.item.name if e.item else None,
                "aliases": [n for n in e.names if n != e.name], "fields": e.page.fields, "sections": sections,
                "ideas": {"facts": [self._fact(f, True) for _, f in e.ideas()], "sections": links["ideas"]},
                "links": {"members": [{"name": m.name, "key": m.key, "type": m.type}
                                      for m in sorted(links["members"].values(), key=lambda m: m.name.casefold())],
                          "dialogues": links["dialogues"],
                          "appears_in": [links["appears_in"][n] for n in sorted(links["appears_in"])]}}

    def findings(self):
        out = list(self.problems)
        cited = any(s.role != "prose" for s in self.sources)
        for s in self.sources:
            if s.role != "prose" and not os.path.isfile(s.path):
                out.append(store.finding("WARN", "PLAN_SOURCE_MISSING", f"source {s.name!r} file not found: "
                                         f"{s.path}; update planning_wiki.sources", self.p.rel(s.path)))
        names = ", ".join(s.name for s in self.sources)
        for e in self.entries:
            for section, f in e.decided() + e.ideas():
                line = e.offset + f["first"] + 1
                if f["kind"] == "fence":
                    continue
                refs = [self.resolve(r) for r in f["refs"]]
                if not refs and cited and section["heading"].lower() != IDEAS:
                    out.append(store.finding("WARN", "PLAN_UNCITED", "a decided fact without a source: end it with "
                                             "[src: <source> §<section>], or move it under ## Ideas", e.page.path, line))
                for r in refs:
                    if r["source"] is None:
                        out.append(store.finding("WARN", "PLAN_SOURCE_UNKNOWN", f"{r['ref']!r} names no source; "
                                                 f"sources: {names}", e.page.path, line))
                    elif not r["found"] and r["role"] != "prose" and os.path.isfile(self.source(r["source"]).path):
                        out.append(store.finding("WARN", "PLAN_SECTION_MISSING", f"{r['source']} has no section "
                                                 f"{r['section']!r}; list its sections with: lore planning-source "
                                                 f"{r['source']!r}", e.page.path, line))
                if refs and section["heading"].lower() != IDEAS and all(r["role"] == "ideas" for r in refs):
                    out.append(store.finding("WARN", "PLAN_IDEA_AS_FACT", "this decided fact cites only undecided "
                                             "material; move it under ## Ideas or cite a decided source",
                                             e.page.path, line))
        return sorted(out, key=lambda f: (f["path"], f["line"], f["code"]))


# ---- edits -----------------------------------------------------------------------------------
def _check_text(text):
    text = wiki._check_text(text)
    if CITE_ANY.search(text):
        raise LoreError("INVALID", "leave the [src: …] citation out of text; pass the refs as source")
    return text


def _check_refs(pl, source):
    refs = [r.strip() for r in source or [] if isinstance(r, str) and r.strip()]
    for r in refs:
        if ";" in r or "[" in r or "]" in r:
            raise LoreError("INVALID", f"give each source ref separately, without ; or brackets: {r!r}")
        if pl.resolve(r)["source"] is None:
            raise LoreError("INVALID", f"{r!r} names no planning source; sources: "
                                       f"{', '.join(s.name for s in pl.sources)}")
    return refs


def page_path(p, pl, type_, name):
    spec = p.schema["types"].get(type_, {})
    sub = spec.get("folder") or spec.get("plural") or type_
    stem = store.DEVICE.sub(r"\1_", store.BAD_FILENAME.sub("-", name).strip(" ."))
    path = os.path.normpath(os.path.join(pl.folder, sub, stem + SUFFIX + ".md"))
    if not store.inside(pl.folder, path):
        raise LoreError("INVALID", f"type {type_!r} has a folder that points outside the planning folder; fix its "
                                   "folder in the settings' types, or use another type")
    return path


def _read(p, e, version):
    path = os.path.join(p.root, e.page.path)
    with open(path, "rb") as fh:
        data = fh.read()
    sha = store.sha256(data)
    if version is not None and version != sha:
        raise LoreError("CONFLICT", f"{e.page.path} changed since it was read; read it again (lore planning "
                                    f"{e.name!r}) and retry", {"version": sha, "path": e.page.path})
    return path, data.decode("utf-8"), sha


def _hit(lines, e, fact):
    for s in parse("\n".join(lines)):
        for f in s["facts"]:
            if f["id"] == str(fact).strip():
                return s, f
    raise LoreError("NOT_FOUND", f"no fact {fact} in {e.name}; it changed since the card was read, so read the card "
                                 "again (lore planning NAME)")


def _id_of(lines, section, text):
    hits = [f for s in parse("\n".join(lines)) if s["heading"].lower() == section.lower() for f in s["facts"]
            if wiki.norm(f["text"]) == wiki.norm(text)]
    return hits[-1]["id"] if hits else None


def _done(p):
    p.__dict__.pop("_plan", None)


def fact(p, item, section=None, text=None, source=None, fact=None, remove=False, type_=None, version=None):
    pl = plan(p)
    refs = _check_refs(pl, source)
    e = pl.find(item)
    if fact is None:
        if remove:
            raise LoreError("INVALID", "remove needs fact: the id from the card (fact:...)")
        section, text = wiki._check_section(section), _check_text(text)
        if not refs and any(s.role != "prose" for s in pl.sources) and section.lower() != IDEAS:
            raise LoreError("INVALID", "give source (e.g. World Bible §23.4): every decided planning fact cites "
                                       "where it comes from")
        if e is None:
            if not type_:
                raise LoreError("NOT_FOUND", f"no planning entry named {item!r}; pass type (e.g. character) to start "
                                             "a planning page for it")
            if not re.fullmatch(r"[a-z_]+", str(type_)):   # planning-only kinds (species, concept) are allowed
                raise LoreError("INVALID", f"type must be lower-case letters, e.g. {', '.join(p.schema['types'])}")
            name = str(item).strip()
            if not name or store.BAD_NAME.search(name):
                raise LoreError("INVALID", "name must be one line without [ ] | # ^ / \\ (they break wikilinks)")
            path, sha = page_path(p, pl, type_, name), None
            if os.path.exists(path):
                raise LoreError("CONFLICT", f"{p.rel(path)} exists but is not a planning page; give it 'type: {type_}'")
            page = fm.update("", set={"type": type_, "canonical_name": name}, body=f"\n# {name}\n")
            created = True
        else:
            path, page, sha = _read(p, e, version)
            name, created = e.name, False
        head, lines, cr = wiki._split(page)
        wiki.append_fact(lines, section, f"- {cite(text, refs)}{cr}", cr)
        new = store.atomic_write(path, head + "\n".join(lines), expect=sha, create=sha is None)
        _done(p)
        return {"item": name, "path": p.rel(path), "version": new, "created": created, "section": section,
                "text": text, "sources": refs, "id": _id_of(lines, section, text)}
    if e is None:
        raise LoreError("NOT_FOUND", f"no planning entry named {item!r}; list entries with: lore planning")
    path, page, sha = _read(p, e, version)
    head, lines, cr = wiki._split(page)
    sec, hit = _hit(lines, e, fact)
    if remove:
        del lines[hit["first"]:hit["last"] + 1]
        new = store.atomic_write(path, head + "\n".join(lines), expect=sha)
        _done(p)
        return {"item": e.name, "path": e.page.path, "version": new, "section": sec["heading"],
                "removed": hit["text"], "sources": hit["refs"]}
    text = _check_text(text)
    refs = refs or hit["refs"]
    lines[hit["first"]:hit["last"] + 1] = [f"- {cite(text, refs)}{cr}"]
    new = store.atomic_write(path, head + "\n".join(lines), expect=sha)
    _done(p)
    return {"item": e.name, "path": e.page.path, "version": new, "created": False, "section": sec["heading"],
            "text": text, "sources": refs, "id": _id_of(lines, sec["heading"], text), "old": hit["text"]}


# ---- impact ----------------------------------------------------------------------------------
def _status(n, written):
    return "frozen" if n <= written else "current" if n == written + 1 else "planned"


def _snip(line):
    line = line.rstrip("\r").strip()
    return line if len(line) <= 300 else line[:297] + "..."


def impact(p, item=None, terms=None, written=None, limit=40):
    pl = plan(p)
    phrases = []
    if item:
        e = pl.get(item)
        phrases += [n for n in e.names if len(re.sub(r"\W", "", n)) >= 3 and n.lower() not in pl.exclude] or [e.name]
    phrases += [t.strip() for t in terms or [] if isinstance(t, str) and t.strip()]
    if not phrases:
        raise LoreError("INVALID", "give item or terms: an entry whose names to search for, or phrases such as "
                                   "\"Mach 20\"")
    if limit < 1:
        raise LoreError("INVALID", "limit must be 1 or more")
    if written is None:   # the last chapter the story wiki has recorded (stamped facts only, not page appearances)
        written = max((x for e in wiki.story(p).entries if e.page is not None for s in e.parsed for f in s["facts"]
                       if f["stamped"] for x in (f["from"], f["to"]) if x is not None), default=0)
    alts = sorted({r"\s+".join(map(re.escape, x.split())) for x in phrases}, key=len, reverse=True)
    rx = re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.I)
    more = {}

    def cap(name, rows):
        more[name] = max(0, len(rows) - limit)
        return rows[:limit]
    hits = [{"entry": e.name, "key": e.key, "section": s["heading"], "id": f["id"], "text": f["text"]}
            for e in pl.entries for s, f in e.decided() if rx.search(f["text"])]
    sources = []
    for s in pl.sources:
        if s.role in ("ideas", "chapters", "prose") or not os.path.isfile(s.path):
            continue
        by = {}
        for i, raw in enumerate(s.lines()):
            if rx.search(raw):
                sec = s.at(i)
                key = sec["line"] if sec else -1
                row = by.setdefault(key, {"section": sec["ref"] if sec else None,
                                          "title": sec["title"] if sec else "(before the first heading)",
                                          "line": i + 1, "lines": []})
                row["lines"].append({"line": i + 1, "text": _snip(raw)})
        if by:
            rows = list(by.values())
            sources.append({"source": s.name, "rank": s.rank, "role": s.role, "hits": rows[:limit],
                            "more": max(0, len(rows) - limit)})
    chapters = []
    for s in pl.sources:
        if s.role == "chapters" and os.path.isfile(s.path):
            for n, title, text, _ in pl._cards(s):
                found = [_snip(x) for x in text.split("\n") if rx.search(x)]
                if found:
                    chapters.append({"n": n, "kind": "card", "title": title, "source": s.name,
                                     "status": _status(n, written), "lines": found})
        elif s.role == "prose":
            for n in range(0, written + 2):
                path = os.path.normpath(os.path.join(p.root, s.pattern.format(n=n)))
                if not os.path.isfile(path):
                    continue
                with open(path, encoding="utf-8", errors="replace") as fh:
                    found = [_snip(x) for x in fh.read().split("\n") if rx.search(x)]
                if found:
                    chapters.append({"n": n, "kind": "prose", "source": s.name, "path": p.rel(path),
                                     "status": _status(n, written), "lines": found})
    chapters.sort(key=lambda c: (c["n"], c["kind"] != "card"))
    pages = []
    for it in p.items:
        found = [_snip(x) for x in it.text.split("\n") if rx.search(x)]
        if found:
            pages.append({"name": it.name, "path": it.path, "lines": found})
    story = wiki.story(p)
    if story.folder:
        for e in story.entries:
            if e.page is None or e.page is e.item:
                continue
            for s in e.parsed:
                for f in s["facts"]:
                    if rx.search(f["text"]):
                        pages.append({"name": e.name, "path": e.page.path, "section": s["heading"],
                                      "text": f["text"], "from": f["from"], "to": f["to"],
                                      "status": _status(f["from"] or 0, written)})
    return {"written": written, "terms": phrases, "planning": cap("planning", hits), "sources": sources,
            "chapters": cap("chapters", chapters), "pages": cap("pages", pages), "limit": limit, "more": more}


# ---- the recorded planning change ------------------------------------------------------------
def _lines(text):
    cr = "\r" if "\r\n" in text else ""
    lines = text.split("\n")
    if lines[-1]:
        lines[-1] += cr
        lines.append("")
    return lines, cr


def _amend(src, sec, note):
    """The source text with note added at the end of the section's own text (before its first subsection and
    its trailing blank lines)."""
    lines, cr = _lines(src.raw)
    stop = next((t["line"] for t in src.sections() if t["line"] > sec["line"]), sec["end"])
    k = max(i for i in range(sec["line"], min(sec["end"], stop, len(lines))) if lines[i].strip() or i == sec["line"])
    add = [cr, note + cr]
    if k + 1 < len(lines) and lines[k + 1].strip():
        add.append(cr)
    lines[k + 1:k + 1] = add
    return "\n".join(lines), k + 3


def _register(reg, block):
    """The register text with block inserted after the newest entry (before any example after it)."""
    lines, cr = _lines(reg.raw)
    ids, examples = reg.entries(), [s["line"] for s in reg.sections() if s["example"] and s["level"] <= 6]
    if ids:   # after the last real entry
        pos = max(s["end"] for s in ids if s["line"] == max(t["line"] for t in ids))
    else:     # the first entry: before an example, else at the end
        pos = min(examples, default=len(lines) - 1)
    pos = min(pos, len(lines) - 1)
    while pos > 0 and not lines[pos - 1].strip():
        pos -= 1
    prev = lines[pos - 1].strip() if pos > 0 else ""
    add = [cr] + ([f"---{cr}", cr] if prev and prev != "---" else []) + [x + cr for x in block] + [cr, f"---{cr}"]
    if pos < len(lines) - 1 and lines[pos].strip():
        add.append(cr)
    lines[pos:pos] = add
    return "\n".join(lines)


def change(p, item, decision=None, fact=None, text=None, remove=False, section=None, terms=None, written=None,
           version=None):
    decision = decision.strip() if isinstance(decision, str) else ""
    if not decision:
        raise LoreError("INVALID", "give decision: the author's own words for this change; they are quoted in the "
                                   "override")
    if fact is None and not (section and text):
        raise LoreError("INVALID", "give fact (its id from the card) with text or remove, or section and text for a "
                                   "new fact")
    if fact is not None and not remove and not text:
        raise LoreError("INVALID", "give the new text, or remove")
    pl = plan(p)
    e = pl.get(item)
    text = _check_text(text) if text and not remove else None
    section = wiki._check_section(section) if fact is None else None
    path, page, sha = _read(p, e, version)
    head, lines, cr = wiki._split(page)
    old = sec = None
    if fact is not None:
        sec, old = _hit(lines, e, fact)
    resolved = [pl.resolve(r) for r in (old["refs"] if old else [])]
    for r in resolved:   # a citation that does not resolve would leave the write-back undone: stop before writing
        if not r["found"] and r["role"] not in ("ideas", "overrides", "prose"):
            raise LoreError("INVALID", f"{e.name}'s fact cites {r['ref']!r}, which does not resolve; fix the citation "
                                       "first (lore planning-source <source> lists the sections), then retry")
    target = min((r for r in resolved if r["found"] and r["role"] not in ("ideas", "overrides", "prose")),
                 key=lambda r: r["rank"], default=None)
    src = pl.source(target["source"]) if target else None
    where = src.find(target["section"]) if src else None
    reg = next((s for s in pl.sources if s.role == "overrides"), None)
    if reg is not None:
        reg.lines()
    hid = reg.next_id() if reg else None
    review = impact(p, item=e.key, terms=terms, written=written)
    written = review["written"]
    today = datetime.date.today().isoformat()
    heading = sec["heading"] if sec else section
    new_text = None if remove else text
    note_text = f"No longer true: {old['text']}" if remove else new_text
    done = []

    def step(label, fn):
        try:
            value = fn()
        except LoreError as exc:
            raise LoreError(exc.code, exc.message + (f" (already written: {', '.join(done)})" if done else ""),
                            exc.data) from exc
        done.append(label)
        return value
    counts = _counts(review)
    if reg is not None:
        quote = decision.splitlines()
        quote[0] = '*"' + quote[0]
        quote[-1] += '"*'
        what = f"{e.name} › {heading}"
        block = [f"**ID:** `{hid}`", "", "**Human decision:**", *[f"> {q}" for q in quote], "",
                 "**Supersedes:** " + (f"{target['ref']}, as the planning wiki states it: \"{old['text']}\""
                                       if target else f"the planning wiki fact \"{old['text']}\"" if old
                                       else "nothing earlier (a new planning fact)"), "",
                 f"**Affected scope:** {what}: " + ("removed." if remove else f"now \"{new_text}\".")
                 + " Only this fact; the impact review lists what else mentions it.", "",
                 f"**Date and chapter context:** {today}, a planning-wiki change; chapters written through {written}.",
                 "", f"**Downstream implications:** impact review: {counts}.", "", "**Status:** `ACTIVE`"]
        step(p.rel(reg.path), lambda: store.atomic_write(reg.path, _register(reg, block), expect=reg.version))
    write_back = None
    if src is not None:
        tag = f"Amended by {hid}" if hid else "Amended"
        amended, line = _amend(src, where, f"> **{tag} ({today}):** {note_text}")
        step(p.rel(src.path), lambda: store.atomic_write(src.path, amended, expect=src.version))
        write_back = {"source": src.name, "section": where["ref"], "title": where["title"], "line": line,
                      "path": p.rel(src.path)}
    refs = ([f"{reg.name} {hid}"] if reg is not None else []) + (old["refs"] if old else [])
    if remove:
        del lines[old["first"]:old["last"] + 1]
    elif old:
        lines[old["first"]:old["last"] + 1] = [f"- {cite(new_text, refs)}{cr}"]
    else:
        wiki.append_fact(lines, section, f"- {cite(new_text, refs)}{cr}", cr)
    new_version = step(e.page.path, lambda: store.atomic_write(path, head + "\n".join(lines), expect=sha))
    _done(p)
    fid = None if remove else _id_of(lines, heading, new_text)
    out = {"override": hid, "item": e.name, "path": e.page.path, "version": new_version, "section": heading,
           "old": old["text"] if old else None, "text": new_text, "removed": bool(remove), "sources": refs,
           "id": fid, "write_back": write_back, "written": written, "impact": review}
    out["report"] = report(out, decision)
    return out


def _counts(review):
    by = {}
    for c in review["chapters"]:
        by[c["status"]] = by.get(c["status"], 0) + 1
    srcs = sum(len(g["hits"]) for g in review["sources"])
    return (f"{len(review['planning'])} planning facts, {srcs} source sections, {by.get('frozen', 0)} frozen chapter "
            f"hits (flagged, approved prose not changed), {by.get('current', 0)} current, {by.get('planned', 0)} planned")


def report(out, decision):
    """The impact review as Markdown for the author and the AI."""
    review = out["impact"]
    title = f"Planning change {out['override']}" if out["override"] else "Planning change"
    lines = [f"# {title}: {out['item']} › {out['section']}", "",
             f"- Decision: \"{' '.join(decision.split())}\""]
    if out["old"]:
        lines.append(f"- Was: {out['old']}")
    lines.append(f"- Now: {'(removed)' if out['removed'] else out['text']}")
    if out["override"]:
        lines.append(f"- Recorded as {out['override']} in the override register")
    wb = out["write_back"]
    lines.append(f"- Written back: {wb['source']} §{wb['section']} ({wb['path']}, line {wb['line']})" if wb
                 else "- Written back: no source section to amend (the fact cited none)")
    lines += [f"- Chapters written through: {out['written']}", f"- Searched for: {', '.join(review['terms'])}", ""]
    lines.append("## Planning facts that mention it (update the ones the change affects)")
    lines += [f"- {h['entry']} › {h['section']}: {h['text']}" for h in review["planning"]] or ["- none"]
    lines += ["", "## Source passages (reconcile them, highest authority first)"]
    for g in review["sources"]:
        lines.append(f"### {g['source']}")
        for h in g["hits"]:
            lines.append(f"- §{h['section']} {h['title']}: " + " / ".join(f"line {x['line']}: {x['text']}"
                                                                         for x in h["lines"][:3]))
        if g["more"]:
            lines.append(f"- and {g['more']} more sections")
    if not review["sources"]:
        lines.append("- none")
    for status, heading in (("frozen", "Frozen chapters (flag to the author; never edit approved prose)"),
                            ("current", "Current chapter (update it, then refresh its sources)"),
                            ("planned", "Planned chapters (update their cards)")):
        lines += ["", f"## {heading}"]
        rows = [c for c in review["chapters"] if c["status"] == status]
        lines += [f"- Chapter {c['n']} ({c['kind']}): " + " / ".join(c["lines"][:3]) for c in rows] or ["- none"]
        story = [h for h in review["pages"] if h.get("status") == status]
        lines += [f"- Story Wiki {h['name']} › {h['section']} [ch {h['from']}]: {h['text']}" for h in story]
    lines += ["", "## Wiki pages that mention it"]
    lines += [f"- {h['name']} ({h['path']}): " + " / ".join(h["lines"][:2]) for h in review["pages"]
              if h.get("from") is None and "lines" in h] or ["- none"]
    return "\n".join(lines) + "\n"
