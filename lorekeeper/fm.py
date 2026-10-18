"""Flat, restricted frontmatter with edits confined to the requested lines."""

from dataclasses import dataclass, field
import re


_KEY = re.compile(r"([a-z_][a-z0-9_]*):(.*)")
_ITEM = re.compile(r"[ \t]*-(?:[ \t]+(.*))?")   # "  - value" under an empty "key:" (Obsidian's lists)
_CLOSE = re.compile(r"^---(?:\r?\n|\Z)", re.MULTILINE)
_WIKILINK = re.compile(r"\[\[([^\[\]\r\n]*)\]\]")
_LINKS = re.compile(r"\[\[[^\[\]\r\n]*\]\](?:[ \t,]*\[\[[^\[\]\r\n]*\]\])+")   # [[A]], [[B]] by hand


class FrontmatterError(ValueError):
    def __init__(self, message: str, line: int = 1):
        super().__init__(message)
        self.line = line


@dataclass
class Frontmatter:
    fields: dict[str, str | list[str]]
    lines: dict[str, int]          # each key's first line; a key missing from fields could not be read
    unsupported: list[int]
    body: str
    newline: str
    ends: dict[str, int] = field(default_factory=dict)   # last "- item" line of each block list


def _block(text):
    opening = re.match(r"\ufeff?---(\r?\n)", text)
    if opening is None:
        return None
    closing = _CLOSE.search(text, opening.end())
    if closing is None:
        raise FrontmatterError("Unterminated frontmatter", line=1)
    # Only LF/CRLF delimit lines; Unicode separators remain ordinary text.
    lines = re.findall(r"[^\n]*\n|[^\n]+$", text[:closing.end()])
    return lines, text[closing.end():], opening.group(1)


def parse(text: str) -> Frontmatter | None:
    block = _block(text)
    if block is None:
        return None
    raw_lines, body, newline = block
    fields, lines, unsupported, ends = {}, {}, [], {}
    owner = None   # the empty "key:" whose "- item" lines may follow
    for number, line in enumerate(raw_lines[1:-1], 2):
        line = line.removesuffix("\n").removesuffix("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = owner and _ITEM.fullmatch(line)
        if item:
            if owner not in ends:
                fields[owner] = []
            fields[owner].append(_unquote((item[1] or "").strip()))
            ends[owner] = number
            continue
        owner = None
        match = _KEY.fullmatch(line)
        if match is None or match[1] in lines:
            unsupported.append(number)
            continue
        key, raw = match[1], match[2].strip(" \t")
        lines[key] = number
        try:
            fields[key] = parse_value(raw)
        except ValueError:   # kept as-is; update() refuses to edit it
            unsupported.append(number)
            continue
        if not raw:
            owner = key
    return Frontmatter(fields, lines, unsupported, body, newline, ends)


def _unquote(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return re.sub(r'\\(["\\])', r'\1', raw[1:-1])
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def _list_item(raw):
    raw = raw.strip()
    value = _unquote(raw)
    if value == raw and raw.count("[") != raw.count("]"):
        raise ValueError(f"list item {raw!r} has unbalanced brackets")
    return value


def parse_value(raw: str) -> str | list[str]:
    """Raises ValueError when an unquoted list item has unbalanced brackets ([[A]], [[B])."""
    if _WIKILINK.fullmatch(raw):
        return raw
    if _LINKS.fullmatch(raw):
        return [m[0] for m in _WIKILINK.finditer(raw)]
    if not (raw.startswith("[") and raw.endswith("]")):
        return _unquote(raw)
    inside = raw[1:-1]
    if not inside.strip():
        return []
    items = []
    start = i = 0
    quote = None
    in_link = False
    while i < len(inside):
        char = inside[i]
        if quote:
            if quote == '"' and char == "\\" and inside[i + 1:i + 2] in ('"', "\\"):
                i += 2
                continue
            if char == quote:
                if quote == "'" and inside[i + 1:i + 2] == "'":
                    i += 2
                    continue
                quote = None
        elif in_link:
            if inside.startswith("]]", i):
                in_link = False
                i += 2
                continue
        elif inside.startswith("[[", i):
            in_link = True
            i += 2
            continue
        elif char in "\"'" and not inside[start:i].strip():   # quotes open a token, never mid-word
            quote = char
        elif char == ",":
            items.append(_list_item(inside[start:i]))
            start = i + 1
        i += 1
    items.append(_list_item(inside[start:]))
    return items


def _format_string(value, in_list=False):
    value = str(value)
    needs_quotes = (
        value.startswith(tuple('[]{}\"\'#&*!|>%@`,'))
        or re.match(r"[-?:](?:[ \t]|\Z)", value)   # YAML "- ", "? " and ": " indicators
        or value.endswith(":") or re.search(r":[ \t]|[ \t]#", value)
        or value != value.strip()
        or (in_list and (not value or value[0] in "?:" or any(c in value for c in ",[]{}\"'")))
    )
    if needs_quotes:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def format_value(value: str | list[str]) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_format_string(item, True) for item in value) + "]"
    return _format_string(value)


def update(text, set=None, unset=(), body=None) -> str:
    changes = set or {}
    removed = frozenset(unset)
    if not changes and not removed and body is None:
        return text
    formatted = {}
    for key, value in changes.items():
        raw = format_value(value)
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", key) or "\n" in raw or "\r" in raw:
            raise ValueError("Frontmatter edits require flat keys and single-line values")
        formatted[key] = f"{key}: {raw}" if raw else f"{key}:"
    fm = parse(text)
    if fm is None:
        # An absent removal is a no-op, even when there is no block yet.
        if not changes and body is None:
            return text
        newline = "\r\n" if "\r\n" in text else "\n"
        bom = "\ufeff" if text.startswith("\ufeff") else ""
        content = text[len(bom):] if body is None else body
        added = "".join(line + newline for key, line in formatted.items() if key not in removed)
        return bom + "---" + newline + added + "---" + newline + content
    for key in [*changes, *removed]:
        if key in fm.lines and key not in fm.fields:
            raise ValueError(f"{key}: line {fm.lines[key]} cannot be read; fix it by hand first")
    raw_lines, _, _ = _block(text)
    for key, number in fm.lines.items():
        last = fm.ends.get(key, number)   # a block list spans its "- item" lines too
        if key in removed:
            raw_lines[number - 1:last] = [""] * (last - number + 1)
        elif key in changes and fm.fields[key] != changes[key]:
            ending = "\r\n" if raw_lines[number - 1].endswith("\r\n") else "\n"
            line = formatted[key]
            if line.endswith(":") and last < len(raw_lines) and _ITEM.fullmatch(raw_lines[last].rstrip("\r\n")):
                line += ' ""'   # a bare "key:" would adopt the "- x" line below it as a list
            raw_lines[number - 1:last] = [line + ending] + [""] * (last - number)
    # Unset wins on overlap; unsupported duplicates remain untouched.
    added = "".join(line + fm.newline for key, line in formatted.items()
                    if key not in fm.fields and key not in removed)
    content = fm.body if body is None else body
    closing = raw_lines[-1]
    # An EOF delimiter needs a line ending before a newly supplied body.
    if content and not closing.endswith("\n"):
        closing += fm.newline
    return "".join(raw_lines[:-1]) + added + closing + content


def link_target(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = _WIKILINK.fullmatch(value)
    if match is None:
        return None
    return match[1].split("|", 1)[0].split("#", 1)[0].rsplit("/", 1)[-1].strip()
