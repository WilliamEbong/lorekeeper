"""Flat, restricted frontmatter with edits confined to the requested lines."""

from dataclasses import dataclass
import re


_KEY = re.compile(r"([a-z_][a-z0-9_]*):(.*)")
_CLOSE = re.compile(r"^---(?:\r?\n|\Z)", re.MULTILINE)
_WIKILINK = re.compile(r"\[\[([^\[\]\r\n]*)\]\]")


class FrontmatterError(ValueError):
    def __init__(self, message: str, line: int = 1):
        super().__init__(message)
        self.line = line


@dataclass
class Frontmatter:
    fields: dict[str, str | list[str]]
    lines: dict[str, int]
    unsupported: list[int]
    body: str
    newline: str


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
    fields, lines, unsupported = {}, {}, []
    for number, line in enumerate(raw_lines[1:-1], 2):
        line = line.removesuffix("\n").removesuffix("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _KEY.fullmatch(line)
        if match is None or match[1] in fields:
            unsupported.append(number)
            continue
        key, raw = match.groups()
        fields[key] = parse_value(raw.strip(" \t"))
        lines[key] = number
    return Frontmatter(fields, lines, unsupported, body, newline)


def _unquote(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return re.sub(r'\\(["\\])', r'\1', raw[1:-1])
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def parse_value(raw: str) -> str | list[str]:
    if _WIKILINK.fullmatch(raw):
        return raw
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
        elif char in "\"'":
            quote = char
        elif char == ",":
            items.append(_unquote(inside[start:i].strip()))
            start = i + 1
        i += 1
    items.append(_unquote(inside[start:].strip()))
    return items


def _format_string(value, in_list=False):
    value = str(value)
    needs_quotes = (
        value.startswith(tuple('[{\"\'#&*!|>%@`,'))
        or ": " in value or " #" in value
        or value != value.strip()
        or (in_list and (not value or "," in value or "]" in value))
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
    raw_lines, _, _ = _block(text)
    for key, number in fm.lines.items():
        if key in removed:
            raw_lines[number - 1] = ""
        elif key in changes and fm.fields[key] != changes[key]:
            ending = "\r\n" if raw_lines[number - 1].endswith("\r\n") else "\n"
            raw_lines[number - 1] = formatted[key] + ending
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
