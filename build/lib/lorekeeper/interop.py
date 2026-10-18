"""Clean-room Aeon containers, CSV interchange, and a readable Markdown export."""
import copy
import csv
import io
import json
import os
import re
import secrets
import string
import struct
import tempfile
import time

from . import dates, fm, store
from .store import LoreError
from .timeinfo import calendar_of, item_dates

DEPENDENCIES = {"FS": "after", "SS": "same_start", "FF": "same_end", "SF": "sf"}
CSV_COLUMNS = ["label", "type", "startDate", "endDate", "summary", "tags", "displayId"]
GREGORIAN = dates.Calendar({})


def _invalid(reason):
    raise LoreError("INVALID", reason)


def _marker(version):
    return b"\x33" * 4 + b"\x11" * 8 + (b"\x22" * 8 if version == 1 else b"HDJDJZWQ")


def _archive(blob, root=False):
    """Return (id, name, payload) entries, validating all boundaries before slicing."""
    if len(blob) < 40:
        _invalid("not an Aeon archive: missing 40-byte header")
    version, size, index_size, count = struct.unpack_from("<IIQI", blob, len(blob) - 40)
    if version not in (1, 2) or size != 40 or blob[-20:] != _marker(version):
        _invalid("not an Aeon archive: invalid header or container version")
    end = len(blob) - 40
    start = end - index_size
    minimum = 36 if root else 52
    if start < 0 or count > index_size // minimum:
        _invalid("invalid Aeon archive index size/count")
    cursor, entries, spans, seen = start, [], [], set()
    for _ in range(count):
        if cursor + minimum > end:
            _invalid("truncated Aeon archive index")
        offset, length = struct.unpack_from("<QQ", blob, cursor)
        if root:
            name_len, = struct.unpack_from("<I", blob, cursor + 32)
            id_len = 0
        else:
            id_len, name_len = struct.unpack_from("<II", blob, cursor + 44)
        cursor += minimum
        if cursor + id_len + name_len > end or offset + length > start:
            _invalid("Aeon archive entry points outside its payload/index")
        try:
            ident = blob[cursor:cursor + id_len].decode("utf-8")
            name = blob[cursor + id_len:cursor + id_len + name_len].decode("utf-8")
        except UnicodeDecodeError as exc:
            _invalid(f"invalid UTF-8 in Aeon archive index: {exc}")
        cursor += id_len + name_len
        key = name if root else ident
        if key in seen:
            _invalid(f"duplicate Aeon archive entry: {key}")
        seen.add(key)
        spans.append((offset, offset + length))
        entries.append((ident, name, blob[offset:offset + length]))
    if cursor != end:
        _invalid("extra bytes in Aeon archive index")
    spans.sort()
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        _invalid("overlapping Aeon archive payloads")
    return entries


def _pack(entries, root=False):
    payload, index = bytearray(), bytearray()
    for ident, name, blob in entries:
        ident, name = ident.encode("utf-8"), name.encode("utf-8")
        index.extend(struct.pack("<QQ", len(payload), len(blob)))
        if root:
            index.extend(b"\0" * 16 + struct.pack("<I", len(name)) + name)
        else:
            index.extend(b"\0" * 28 + struct.pack("<II", len(ident), len(name)) + ident + name)
        payload.extend(blob)
    return bytes(payload + index + struct.pack("<IIQI", 1, 40, len(index), len(entries)) + _marker(1))


def _ordered(order):
    return sorted(order, key=lambda k: (order[k], k)) if isinstance(order, dict) else list(order or [])


def _tree_order(tree, fallback=()):
    # Iterative traversal tolerates deep trees and ignores duplicate/cyclic edges.
    roots = [key for key, node in tree.items() if node.get("super") not in tree]
    rank = {key: n for n, key in enumerate(dict.fromkeys(fallback))}
    roots.sort(key=lambda key: rank.get(key, len(rank)))
    stack, seen, result = list(reversed(roots + list(fallback))), set(), []
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
        stack.extend(reversed(_ordered(tree.get(key, {}).get("childOrder", {}))))
    return result


def _date_text(value, calendar):
    if not value:
        return None
    eras = calendar.get("eras", [{}, {}])
    era_index = value.get("era", len(eras) - 1)
    if not isinstance(era_index, int) or not 0 <= era_index < len(eras):
        _invalid(f"invalid Aeon date era: {era_index!r}")
    era = eras[era_index]
    year = int(value["year"])
    if era.get("isBackwards"):
        year = 1 - year
    precision = value.get("precision", 5)
    if precision == -1:
        precision = 7
    month = int(value.get("month", 1)) if precision >= 3 else 1
    day = int(value.get("day", 1)) if precision >= 4 else 1
    hour = int(value.get("hour", 0)) if precision >= 6 else 0
    minute = int(value.get("minute", 0)) if precision >= 7 else 0
    axis = GREGORIAN.to_axis(year, month, day, hour, minute)
    # Lorekeeper has minute resolution. Seconds are intentionally truncated;
    # century/decade/week/hour precision is represented by an inclusive range.
    if precision in (0, 1):
        width = 100 if precision == 0 else 10
        return GREGORIAN.format(axis, "year") + ".." + GREGORIAN.format(
            GREGORIAN.to_axis(year + width - 1, 1, 1), "year")
    if precision in (4, 6):
        unit, width = ("day", 6 * 1440) if precision == 4 else ("minute", 59)
        return GREGORIAN.format(axis, unit) + ".." + GREGORIAN.format(axis + width, unit)
    unit = {2: "year", 3: "month", 5: "day", 7: "minute", 8: "minute", -1: "minute"}.get(precision)
    if unit is None:
        _invalid(f"unsupported Aeon date precision: {precision}")
    return GREGORIAN.format(axis, unit)


def read_aeon(path):
    """Read either container version and normalize v14/v27 core records."""
    try:
        with open(path, "rb") as fh:
            root = {name: blob for _, name, blob in _archive(fh.read(), root=True)}
        if set(root) != {"attachments", "timeline"}:
            _invalid("Aeon archive needs attachments and timeline archives")
        timeline = _archive(root["timeline"])
        attachments = _archive(root["attachments"])
        if len(timeline) != 1 or timeline[0][0] != "timeline3.json":
            _invalid("Aeon timeline archive needs exactly one timeline3.json")
        document = json.loads(timeline[0][2].decode("utf-8"))
        if document.get("fileVersion") not in (14, 27):
            _invalid(f"unsupported Aeon fileVersion: {document.get('fileVersion')!r} (expected 14 or 27)")
        core = document["core"]
        definitions, data = core["definitions"], core["data"]
        calendar = definitions["calendar"]
        items = data["itemsById"]
        if document["fileVersion"] == 14:
            order = [key for group in data.get("itemOrderByType", {}).values() for key in _ordered(group)]
            tree = data.get("superAndChildOrderById", {})
        else:
            order = _ordered(data.get("customOrder", {}))
            tree = {key: {"super": parent, "childOrder": {}} for key, parent in data.get("superById", {}).items()}
            for key in dict.fromkeys(order + list(items)):
                parent = tree.get(key, {}).get("super")
                if parent in tree:
                    tree[parent]["childOrder"][key] = len(tree[parent]["childOrder"])
        ordered = _tree_order(tree, order + list(items))
        result = {"calendar": calendar, "types": definitions["types"]["byId"],
                  "roles": definitions["references"]["byId"], "properties": definitions["properties"]["byId"],
                  "items": [], "relationships": [], "dependencies": [],
                  "narrative": [key for key in _tree_order(data.get("narrative", {}).get("sacOrderById", {})) if key in items],
                  "attachments": [name for _, name, _ in attachments]}
        for key in ordered:
            if key not in items:
                continue
            item = items[key]
            times = data.get("itemDatesById", {}).get(key, {})
            result["items"].append({"id": key, "type": item["type"], "name": item["label"],
                                    "summary": item.get("summary", ""),
                                    "tags": [data.get("tags", {}).get(tag, tag) for tag in (item.get("tags") or [])],
                                    "fields": item.get("propertyValues") or {},
                                    "start": _date_text(times.get("startDate"), calendar),
                                    "end": _date_text(times.get("endDate"), calendar)})
        result["relationships"] = [{"subject": r["subject"], "role": r["reference"], "object": r["object"]}
                                   for r in data.get("relationshipsById", {}).values()]
        result["dependencies"] = [{"subject": r["subject"], "object": r["object"], "kind": r["dependencyType"]}
                                  for r in data.get("dependenciesById", {}).values()]
        return result
    except OSError as exc:
        raise LoreError("IO_ERROR", str(exc)) from exc
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, struct.error) as exc:
        raise LoreError("INVALID", f"invalid Aeon file: {exc}") from exc


def _token():
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(21))


def _calendar():
    # Written from Gregorian rules; no template definitions/content are embedded.
    names = "January February March April May June July August September October November December".split()
    lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return {"eras": [{"name": name, "shortName": name, "isBackwards": backwards,
                      "hasLeapYears": True, "leapOffset": int(backwards), "duration": 2 ** 53}
                     for name, backwards in (("BC", True), ("AD", False))],
            "months": [{"name": name, "shortName": name[:3], "normalDuration": length,
                        "leapDuration": length + (i == 1)} for i, (name, length) in enumerate(zip(names, lengths))],
            "weekdays": [{"name": name, "shortName": name[:3]} for name in
                         "Sunday Monday Tuesday Wednesday Thursday Friday Saturday".split()],
            "leapCycles": [4, 100, 400], "hoursInDay": 24, "weekdayIndexAtZero": 1,
            "zeroDateTimestamp": 0, "calendarType": 0, "maxPrecision": 8, "ignoreEras": False,
            "dateFormat": "Medium", "timeFormat": "TwentyFour", "dateOrder": "YearMonthDay",
            "dateFormatIncludesDayName": False, "defaultToModernCentury": False,
            "thousandSeparatorFormat": "Comma", "overrideNowTimestamp": None}


def _aeon_date(when):
    if when is None:
        return None
    parts = GREGORIAN.from_axis(when.lo)
    year = parts["year"]
    precision = {"year": 2, "month": 3, "day": 5, "hour": 6, "minute": 7}[when.precision]
    if when.precision == "minute" and when.hi - when.lo == 60:
        precision = 6
    return {**parts, "year": year if year > 0 else 1 - year, "era": 1 if year > 0 else 0,
            "second": 0, "timestamp": when.lo * 60 + (86400 if year <= 0 else 0),
            "weekday": (when.lo // 1440 + 1) % 7, "precision": precision}


def _narrative(project):
    path = os.path.join(project.root, "narrative.md")
    if not store.inside(project.root, path):
        _invalid("narrative.md is outside the project")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return []
    result = []
    for link in re.findall(r"\[\[[^\[\]\r\n]+\]\]", text):
        item = project.resolve(fm.link_target(link))
        if item is not None and item not in result:
            result.append(item)
    return result


def _collection(records):
    return {"byId": records, "sortOrder": {key: i for i, key in enumerate(records)}}


def write_aeon(project, path):
    """Write a minimal v14 core, leaving migration/UI defaults to Aeon."""
    schema = project.schema
    ids = {id(item): _token() for item in project.items}
    type_ids = {key: _token() for key in schema["types"]}
    role_ids = {key: _token() for key in schema["roles"] if key not in DEPENDENCIES.values()}
    prop_ids = {key: _token() for key in schema["properties"]}
    tag_ids = {}
    chapter_label, scene_label = _token(), _token()
    definitions = {"calendar": _calendar(), "includeNarrative": True, "colors": _collection({}),
                   "autoAdjustLevel": 0, "autoAdjustBackwardsLimit": "Off", "storeRelativePaths": False,
                   "defaultColumns": {}, "narrativeSettings": {"labels": {
                       chapter_label: {"id": chapter_label, "label": "Chapter", "autoForFolder": True,
                                       "autoForOther": False, "sortOrder": 0},
                       scene_label: {"id": scene_label, "label": "Scene", "autoForFolder": False,
                                     "autoForOther": True, "sortOrder": 1}}, "numbering": "OUTLINE_STYLE",
                   "autoDeleteWhenRemoveContainer": False, "strictFolderStructure": False}}
    definitions["types"] = _collection({type_ids[key]: {
        "id": type_ids[key], "label": spec.get("label", key), "pluralLabel": spec.get("plural", key),
        "identifierPrefix": spec.get("id_prefix", key.upper()), "enabled": True, "canDelete": True,
        "references": dict.fromkeys(role_ids.values(), True), "properties": dict.fromkeys(prop_ids.values(), True),
        "superTypes": {}, "canHaveDate": spec.get("category") in ("person", "event"),
        "canIncludeInNarrative": True, "isNarrativeFolder": spec.get("category") == "narrative",
        "category": {"person": "PERSON", "place": "LOCATION"}.get(spec.get("category"), "OTHER"),
        "icon": "circle filled", "defaultItemColor": "", "showOnSidebar": True, "showAsColumn": False,
        "compactDisplay": "SHORT_LABEL", "showInSequence": True, "columnIsVisible": False,
        "defaultSequenceType": key == "event", "defaultNarrativeType": key == "chapter",
        "labelDisplayLabel": "Label", "startDisplayLabel": "Start", "endDisplayLabel": "End",
        "anniversaryDisplayLabel": "Anniversary", "extendAnniversaryBeyondEnd": False, "canHaveLocationUri": False}
        for key, spec in schema["types"].items()})
    definitions["references"] = _collection({rid: {"id": rid, "label": key, "enabled": True,
        "canDelete": True, "types": {type_ids[t]: True for t in schema["roles"][key].get("to", []) if t in type_ids},
        "bidirectional": False, "inverseLabel": schema["roles"][key].get("inverse", ""),
        "showInverse": True, "showInInspector": True, "color": "", "icon": "circle filled",
        "lineStyle": "lineStyle_SOLID"} for key, rid in role_ids.items()})
    definitions["properties"] = _collection({pid: {"id": pid, "label": key, "enabled": True,
        # Dates already live in itemDatesById. Their original property text can
        # include circa/ranges/custom calendars, so these properties stay text.
        "canDelete": True, "format": "text" if schema["properties"][key].get("format") == "date"
        else schema["properties"][key].get("format", "text"), "allowed": {},
        "multiple": False, "autoCalculate": False, "autoCalculateType": None, "indicateItemCompletion": False}
        for key, pid in prop_ids.items()})
    data = {key: {} for key in ("itemsById", "itemOrderByType", "itemDatesById", "superAndChildOrderById",
            "relationshipsById", "sequenceOrder", "tags", "calendarMarkers", "savedFiltersById",
            "dependenciesById", "dateConstraintsById", "attachmentsById")}
    data.update(mindmaps=_collection({}), calendarMarkers=_collection({}),
                itemOrderByType={ident: {} for ident in type_ids.values()}, timelineRange={"from": None, "to": None},
                lastTodayDate=_aeon_date(GREGORIAN.parse("2000-01-01")),
                narrative={"label": "Narrative", "sacOrderById": {"narrativeRoot": {"super": None, "childOrder": {}}}})
    for n, item in enumerate(project.items):
        if item.type not in type_ids:
            _invalid(f"unknown type {item.type!r}; add it to lore.json before exporting")
        ident = ids[id(item)]
        tags = item.fields.get("tags") or []
        tags = tags if isinstance(tags, list) else [tags]
        for tag in tags:
            if tag not in tag_ids:
                tag_ids[tag] = _token()
            data["tags"][tag_ids[tag]] = tag
        data["itemsById"][ident] = {"id": ident, "type": type_ids[item.type], "label": item.name,
            "summary": item.body, "displayId": item.id, "internalId": n + 1, "color": "",
            "tags": dict.fromkeys((tag_ids[tag] for tag in tags), True),
            "propertyValues": {prop_ids[k]: v for k, v in item.fields.items() if k in prop_ids},
            "links": {}, "attachments": {}, "image": None, "narrativeLabel": "automatic", "initials": None,
            "shortLabel": None, "showAnniversary": False, "anniversaryIcon": "markerOther", "locationUri": None}
        data["itemOrderByType"].setdefault(type_ids[item.type], {})[ident] = n
        data["superAndChildOrderById"][ident] = {"super": None, "childOrder": {}}
        data["sequenceOrder"][ident] = n
        start, end, bad = item_dates(project, item)
        if bad:
            _invalid(f"cannot export unparsed dates for {item.name}: {bad}")
        if start or end:
            # Aeon has no circa flag. Export the stated date, not the earlier
            # uncertainty bound; the original text remains in its date property.
            def nominal(when):
                if when and when.circa:
                    text = re.sub(r"^(?:~|c\.|ca\.|circa\b|about\b|approximately\b|approx\.|around\b)\s*", "", when.text, flags=re.I)
                    return dates.parse(text, project.calendars) or when
                return when
            start_date, end_date = _aeon_date(nominal(start)), _aeon_date(nominal(end))
            duration = None
            if start_date and end_date:
                days, seconds = divmod(end_date["timestamp"] - start_date["timestamp"], 86400)
                hours, seconds = divmod(seconds, 3600)
                minutes, seconds = divmod(seconds, 60)
                duration = dict(years=0, months=0, weeks=0, days=days, hours=hours, minutes=minutes, seconds=seconds)
            data["itemDatesById"][ident] = {"startDate": start_date, "endDate": end_date,
                "duration": duration, "ongoing": False, "hasOngoingDescendants": False, "isDateLocked": False,
                "preferredStartDate": start_date, "preferredEndDate": end_date, "preferredDuration": duration,
                "latestFixedChildDate": None, "durationToEarliestEnd": None, "latestStartDate": None,
                "earliestEndDate": None, "preferredPrecision": -1}
        for role, targets in project.links(item).items():
            for _, other, _lag in targets:
                # Broken links have no Aeon endpoint. Aeon's dependency triples
                # do not carry Lorekeeper lag text, so only their kind is exported.
                if other is None:
                    continue
                rid = _token()
                record = {"id": rid, "subject": ident, "object": ids[id(other)]}
                if role in DEPENDENCIES.values():
                    record["dependencyType"] = next(k for k, v in DEPENDENCIES.items() if v == role)
                    data["dependenciesById"][rid] = record
                elif role in role_ids:
                    record["reference"] = role_ids[role]
                    data["relationshipsById"][rid] = record
    tree = data["narrative"]["sacOrderById"]
    for n, item in enumerate(_narrative(project)):
        ident = ids[id(item)]
        tree["narrativeRoot"]["childOrder"][ident] = n
        tree[ident] = {"super": "narrativeRoot", "childOrder": {}}
    document = {"fileVersion": 14, "core": {"coreFileVersion": 14, "definitions": definitions, "data": data,
                "templateDetails": {"category": "", "name": ""}, "projectId": _token()}}
    payload = (json.dumps(document, ensure_ascii=False) + "\n").encode("utf-8")
    blob = _pack([("", "attachments", _pack([])), ("", "timeline", _pack([("timeline3.json", "", payload)]))], root=True)
    # Binary counterpart of store.atomic_write: stage beside the destination, then replace.
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".lk-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        for attempt in (1, 2):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.5)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _key(label):
    # store.clean_fields currently allows letters/underscores, not digits.
    return re.sub(r"[^a-z]+", "_", str(label).lower()).strip("_") or "imported"


def _field(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else [_field(v) for v in value]
    text = "" if value is None else str(value)
    # Flat frontmatter cannot hold multiline properties; keep their exact text as JSON.
    return json.dumps(text, ensure_ascii=False) if "\n" in text or "\r" in text else text


def import_into(project, data, into=None):
    """Create new items only; skipped subjects and their existing files remain untouched.

    `into` is a project-relative destination folder, not a second project root.
    CSV extra columns are classified using the destination's schema at import time.
    """
    config = copy.deepcopy(project.config)
    schema = copy.deepcopy(project.schema)
    folder = os.path.join(project.root, into) if into is not None else None
    if folder is not None and not store.inside(project.root, folder):
        _invalid("import destination must be inside the project")
    warnings, mapped_types, mapped_roles, mapped_props = [], {}, {}, {}
    csv_source = data.get("calendar") is None
    for key, spec in data.get("types", {}).items():
        mapped = key if csv_source else {"PERSON": "character", "LOCATION": "location"}.get(spec.get("category"))
        # older templates leave category OTHER even for people and places: fall back to the name
        names = {str(spec.get("label", "")).lower(), str(key).lower()}
        mapped = mapped or next((t for t, words in (("character", {"character", "person", "people", "defaultperson"}),
                                                   ("location", {"place", "location", "defaultlocation"}))
                                 if names & words), None)
        mapped = mapped or ("event" if spec.get("canHaveDate") else _key(spec.get("label", key)))
        mapped_types[key] = mapped
        if mapped not in schema["types"]:
            schema["types"][mapped] = {"label": spec.get("label", mapped), "plural": mapped,
                                       "category": "thing", "id_prefix": mapped.upper()}
            config.setdefault("types", {})[mapped] = schema["types"][mapped]
    for section, mapping in (("roles", mapped_roles), ("properties", mapped_props)):
        used = set()
        for key, spec in data.get(section, {}).items():
            mapped = key if csv_source else _key(spec.get("label", key))
            if section == "roles" and mapped == "participant":
                mapped = "participants"
            if mapped in store.RESERVED and not (section == "properties" and mapped == "status"):
                mapped = "imported_" + mapped
            other_section = "properties" if section == "roles" else "roles"
            while mapped in used or mapped in schema[other_section]:
                mapped += "_imported"
            used.add(mapped)
            mapping[key] = mapped
            if mapped not in schema[section]:
                value = {"label": spec.get("label", mapped)}
                if section == "roles":
                    value.update(to=[mapped_types[t] for t in spec.get("types", {}) if t in mapped_types],
                                 inverse=spec.get("inverseLabel", ""))
                else:
                    value["format"] = spec.get("format", "text")
                schema[section][mapped] = value
                config.setdefault(section, {})[mapped] = value
    # Validate names/fields before touching lore.json or any item file.
    pending, targets, claimed = [], {}, dict(project.by_name)
    skipped = 0
    for record in data.get("items", []):
        name = str(record["name"]).strip()
        ident = record["id"]
        if not name or store.BAD_NAME.search(name):
            _invalid(f"imported name cannot be represented as a wikilink: {name!r}")
        existing = project.resolve(name) or claimed.get(name.lower())
        if existing:
            skipped += 1
            warnings.append(f"WARN skipped existing name: {name}")
            targets[ident] = existing.name if hasattr(existing, "name") else existing
            continue
        claimed[name.lower()] = name
        targets[ident] = name
        type_ = mapped_types.get(record["type"], record["type"])
        if type_ not in schema["types"]:
            _invalid(f"import has undefined type: {type_}")
        fields = {}
        for key, value in record.get("fields", {}).items():
            mapped = mapped_props.get(key, key)
            if mapped in store.RESERVED and mapped != "status":
                continue
            if csv_source and mapped not in schema["properties"] and mapped not in schema["roles"]:
                continue
            fields[mapped] = _field(value)
        fields["tags"] = record.get("tags") or []
        person = schema["types"][type_].get("category") == "person"
        for key, value in (("born" if person else "date", record.get("start")),
                           ("died" if person else "end", record.get("end"))):
            if value and key not in fields:
                fields[key] = value
        pending.append((ident, type_, name, fields, record.get("summary") or ""))
    by_id = {row[0]: row for row in pending}
    for link in data.get("relationships", []) + data.get("dependencies", []):
        subject = by_id.get(link["subject"])
        if subject is None:
            continue
        target = targets.get(link["object"])
        role = DEPENDENCIES.get(link.get("kind")) if "kind" in link else mapped_roles.get(link["role"], link["role"])
        if target is None or not role:
            warnings.append(f"WARN skipped unresolved link from {subject[2]}")
            continue
        values = subject[3].setdefault(role, [])
        if not isinstance(values, list):
            values = subject[3][role] = [values]
        value = f"[[{target}]]"
        if value not in values:
            values.append(value)
    for _, _, _, fields, _ in pending:
        store.clean_fields(fields)
    if folder is not None:
        # Keep newly imported files visible when the project scans selected paths.
        rel = project.rel(folder)
        paths = config.get("paths", ["."])
        if not any(store.inside(os.path.join(project.root, base), folder) for base in paths):
            config["paths"] = paths + [rel]
    cfg_path = os.path.join(project.root, store.CONFIG)
    if not store.inside(project.root, cfg_path):
        _invalid("lore.json is outside the project")
    if config != project.config or not os.path.exists(cfg_path):
        store.atomic_write(cfg_path, json.dumps(config, ensure_ascii=False, indent=2) + "\n", expect=store.file_sha(cfg_path))
    project.config, project.schema = config, store.merged_schema(config)
    writer = project
    if folder is not None:
        local = copy.deepcopy(config)
        local["paths"] = [project.rel(folder)]
        # Type folders stay underneath --into, including custom absolute folders.
        local["types"] = {key: {**spec, "folder": _key(key), "plural": _key(key)} for key, spec in project.schema["types"].items()}
        writer = store.Project.from_items(project.root, local, project.items)
    for _, type_, name, fields, body in pending:
        item = writer.create(type_, name, fields, body)
        writer.items.append(item)
        writer._index()  # create() intentionally does not mutate the Project index.
    project.items = writer.items
    project._index()
    narrative = [targets[key] for key in data.get("narrative", []) if key in targets]
    if narrative:
        path = os.path.join(project.root, "narrative.md")
        if not store.inside(project.root, path):
            _invalid("narrative.md is outside the project")
        # Append new narrative links so importing another file never erases an outline.
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except FileNotFoundError:
            text = "# Narrative\n"
        existing = {fm.link_target(link) for link in re.findall(r"\[\[[^\[\]\r\n]+\]\]", text)}
        added = list(dict.fromkeys(name for name in narrative if name not in existing))
        if added:
            store.atomic_write(path, text.rstrip("\r\n") + "\n" + "".join(f"- [[{name}]]\n" for name in added),
                               expect=store.file_sha(path))
    if data.get("attachments"):
        warnings.append("WARN attachments were not imported: " + ", ".join(data["attachments"]))
    return {"created": len(pending), "skipped": skipped, "warnings": warnings}


def _csv_value(value):
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value


def _csv_date(project, when):
    if when is None:
        return ""
    original = dates.parse(when.text, project.calendars)
    if original and (original.lo, original.hi) == (when.lo, when.hi):
        return when.text
    # item_dates can derive an end from duration while retaining the start's text.
    return calendar_of(project, when).format(when.lo, when.precision)


def write_csv(project, path):
    columns = list(dict.fromkeys(CSV_COLUMNS + list(project.schema["roles"]) + list(project.schema["properties"])))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for item in project.items:
        start, end, _ = item_dates(project, item)
        row = {key: _csv_value(value) for key, value in item.fields.items() if key in columns and key not in CSV_COLUMNS}
        row.update(label=item.name, type=item.type, startDate=_csv_date(project, start), endDate=_csv_date(project, end),
                   summary=item.body, tags=_csv_value(item.fields.get("tags", [])), displayId=item.id)
        writer.writerow(row)
    store.atomic_write(path, "\ufeff" + output.getvalue())


def read_csv(path):
    result = {"calendar": None, "types": {}, "roles": {}, "properties": {}, "items": [],
              "relationships": [], "dependencies": [], "narrative": [], "attachments": []}
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            # Strip only the BOM; keep embedded newlines for csv's quoted-cell parser.
            if fh.read(1) != "\ufeff":
                fh.seek(0)
            reader = csv.DictReader(fh, strict=True)
            if not reader.fieldnames or not {"label", "type"} <= set(reader.fieldnames):
                _invalid("CSV needs label and type columns")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                _invalid("CSV contains duplicate columns")
            for n, row in enumerate(reader, 1):
                if None in row or any(value is None for value in row.values()):
                    _invalid(f"CSV row {n} has the wrong number of cells")
                fields = {}
                for key, value in row.items():
                    if key in CSV_COLUMNS or not value:
                        continue
                    try:
                        decoded = json.loads(value)
                    except ValueError:
                        decoded = value
                    fields[key] = decoded if isinstance(decoded, list) else value
                tags = row.get("tags", "")
                try:
                    tags = json.loads(tags)
                except ValueError:
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                if not isinstance(tags, list):
                    tags = [str(tags)]
                type_ = row["type"].strip()
                if not type_:
                    _invalid(f"CSV row {n} has an empty type")
                result["types"][type_] = {"label": type_}
                # Row ids, not displayId: spreadsheets may contain duplicate/empty display ids.
                result["items"].append({"id": str(n), "type": type_, "name": row["label"],
                    "summary": row.get("summary", ""), "tags": tags, "fields": fields,
                    "start": row.get("startDate") or None, "end": row.get("endDate") or None})
        return result
    except OSError as exc:
        raise LoreError("IO_ERROR", str(exc)) from exc
    except (UnicodeError, csv.Error) as exc:
        raise LoreError("INVALID", f"invalid CSV: {exc}") from exc


def write_markdown(project, path):
    rows = [(item_dates(project, item)[0], item) for item in project.items]
    rows.sort(key=lambda row: (row[0] is None, row[0].lo if row[0] else 0, row[1].name.lower()))
    lines = ["# Timeline", "", "| Date | Name | Type | Location | Participants |", "| --- | --- | --- | --- | --- |"]

    def cell(value):
        return str(value).replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")

    for start, item in rows:
        links = project.links(item)
        values = [start.text if start else "", item.name, item.type]
        values += [", ".join(other.name if other else name for name, other, _ in links.get(role, []))
                   for role in ("location", "participants")]
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    lines += ["", "# Items", ""]
    for _, item in rows:
        lines += [f"## {item.name}", ""]
        lines += [f"- **{key}**: {fm.format_value(value)}" for key, value in item.fields.items()]
        lines += ["", item.body, ""]
    store.atomic_write(path, "\n".join(lines))
