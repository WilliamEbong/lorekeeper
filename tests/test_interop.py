"""Interop acceptance tests. Proprietary templates are inspected only in memory."""
import copy
import csv
import io
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
import unittest
from unittest import mock

from lorekeeper import checks, dates, interop, store
from lorekeeper.timeinfo import item_dates

FIXTURE = Path(__file__).parent / "fixtures" / "world"
OURS = Path(__file__).parent / "fixtures" / "ours"
TEMPLATES = Path(r"C:\Users\Owner\lk-scratch\aeon_extract\3003")


def archive(entries, root=False, version=1):
    """Independent fixture encoder, including the v2 stored-size field."""
    payload, index = b"", b""
    for ident, name, content in entries:
        ident, name = ident.encode("utf-8"), name.encode("utf-8")
        if root:
            index += struct.pack("<QQQQI", len(payload), len(content), 0, 0, len(name)) + name
        else:
            extra = bytearray(28)
            if version == 2:
                struct.pack_into("<Q", extra, 12, len(content))
            index += struct.pack("<QQ", len(payload), len(content)) + extra
            index += struct.pack("<II", len(ident), len(name)) + ident + name
        payload += content
    marker = b"\x33" * 4 + b"\x11" * 8 + (b"\x22" * 8 if version == 1 else b"HDJDJZWQ")
    return payload + index + struct.pack("<IIQI", version, 40, len(index), len(entries)) + marker


def container(document, version=1, attachments=()):
    timeline = json.dumps(document, ensure_ascii=False).encode("utf-8") + b"\n"
    return archive([("", "attachments", archive(attachments, version=version)),
                    ("", "timeline", archive([("timeline3.json", "", timeline)], version=version))],
                   root=True, version=version)


def timeline_json(blob):
    """Independent test decoder: locate root timeline and its first leaf payload."""
    index_size, = struct.unpack_from("<Q", blob, len(blob) - 32)
    cursor = len(blob) - 40 - index_size
    count, = struct.unpack_from("<I", blob, len(blob) - 24)
    for _ in range(count):
        offset, size, _, _, length = struct.unpack_from("<QQQQI", blob, cursor)
        name = blob[cursor + 36:cursor + 36 + length]
        cursor += 36 + length
        if name == b"timeline":
            child = blob[offset:offset + size]
            child_index, = struct.unpack_from("<Q", child, len(child) - 32)
            start, length = struct.unpack_from("<QQ", child, len(child) - 40 - child_index)
            return json.loads(child[start:start + length])
    raise AssertionError("no timeline entry")


def sample(version=14):
    items = {key: {"id": key, "type": "ev", "label": name, "summary": "", "tags": {}, "propertyValues": {}}
             for key, name in (("a", "First"), ("b", "Second"), ("c", "Third"))}
    data = {"itemsById": items, "itemDatesById": {"a": {"startDate": {
        "era": 1, "year": 2004, "month": 2, "day": 29, "hour": 16, "minute": 23,
        "precision": 7, "timestamp": -999999999}}},
        "relationshipsById": {}, "dependenciesById": {}, "narrative": {"sacOrderById": {
            "narrativeRoot": {"super": None, "childOrder": {"b": 0}},
            "b": {"super": "narrativeRoot", "childOrder": {"a": 0}},
            "a": {"super": "b", "childOrder": {}}}}}
    if version == 14:
        data.update(itemOrderByType={"ev": {"c": 0, "b": 1, "a": 2}},
                    superAndChildOrderById={"c": {"super": None, "childOrder": {}},
                                            "b": {"super": None, "childOrder": {"a": 0}},
                                            "a": {"super": "b", "childOrder": {}}})
    else:
        data.update(customOrder={"c": 0, "b": 1, "a": 2}, superById={"a": "b", "b": None, "c": None})
    return {"fileVersion": version, "core": {"coreFileVersion": version, "definitions": {
        "calendar": interop._calendar(), "types": {"byId": {"ev": {"label": "Event", "canHaveDate": True}}},
        "references": {"byId": {}}, "properties": {"byId": {}}}, "data": data}}


class InteropTests(unittest.TestCase):
    def setUp(self):
        # Keep all generated files, including temporary project copies, in the allowlisted tree.
        OURS.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=OURS)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.world = self.root / "world"
        shutil.copytree(FIXTURE, self.world)
        self.project = store.Project(self.world)

    def empty(self, name="empty", config=None):
        root = self.root / name
        root.mkdir()
        store.atomic_write(root / "lore.json", json.dumps(config or {"lorekeeper": 1}))
        return store.Project(root)

    def read_document(self, document, version=1, attachments=()):
        path = self.root / "synthetic.aeon"
        path.write_bytes(container(document, version, attachments))
        return interop.read_aeon(path)

    def assert_invalid(self, path, message=None):
        with self.assertRaises(store.LoreError) as caught:
            interop.read_aeon(path)
        self.assertEqual(caught.exception.code, "INVALID")
        if message:
            self.assertIn(message, caught.exception.message)

    @unittest.skipUnless(TEMPLATES.is_dir(), "Aeon bundled templates are not extracted")
    def test_sc1_all_nineteen_templates(self):
        paths = [path for path in sorted(TEMPLATES.glob("*.bin")) if path.read_bytes()[-20:-16] == b"\x33" * 4]
        self.assertEqual(len(paths), 19)
        for path in paths:
            with self.subTest(template=path.name):
                raw = timeline_json(path.read_bytes())["core"]["data"]
                result = interop.read_aeon(path)
                self.assertEqual(len(result["items"]), len(raw["itemsById"]))
                by_id = {item["id"]: item for item in result["items"]}
                for ident, record in raw["itemDatesById"].items():
                    for source, dest in (("startDate", "start"), ("endDate", "end")):
                        if record.get(source):
                            if dest == "end" and by_id[ident]["end"] is None:
                                # A zero-duration end (a point, or a living person) is dropped.
                                self.assertEqual(interop._date_text(record[source], result["calendar"]),
                                                 by_id[ident]["start"])
                                continue
                            self.assertIsNotNone(dates.parse(by_id[ident][dest], self.project.calendars))
                with tempfile.TemporaryDirectory() as folder:   # outside the repository: Aeon content never enters it
                    store.atomic_write(Path(folder, "lore.json"), json.dumps({"lorekeeper": 1}))
                    self.assertEqual(interop.import_into(store.Project(folder), result)["created"], len(result["items"]))
                    loaded = store.Project(folder)
                    nested = sum(len(loaded.links(i).get(role, [])) for i in loaded.items for role in ("part_of", "located_in"))
                    self.assertGreaterEqual(nested, sum(1 for item in result["items"] if item["parent"]))
                    self.assertEqual([f for f in loaded.findings() if f["code"] in ("BROKEN_LINK", "ROLE_TYPE")
                                      and f["detail"].startswith(("part_of ", "located_in "))], [])

    def test_sc2_aeon_roundtrip_and_import(self):
        store.atomic_write(self.world / "narrative.md", "# Narrative\n- [[Crossing Harrow Pass]]\n- [[The flood at Saltmarsh]]\n")
        # Exercise all dependency kinds; the base fixture already has FS with a lag.
        crossing = self.project.find("Crossing Harrow Pass")
        self.project.update(crossing, {role: "[[The flood at Saltmarsh]]" for role in ("same_start", "same_end", "sf")})
        self.project = store.Project(self.world)
        path = self.root / "world.aeon"
        interop.write_aeon(self.project, path)
        doc = timeline_json(path.read_bytes())
        self.assertEqual(doc["fileVersion"], 14)
        self.assertEqual(set(doc), {"fileVersion", "core"})
        core = doc["core"]
        self.assertEqual(set(core["data"]), {"itemsById", "itemOrderByType", "itemDatesById",
            "superAndChildOrderById", "relationshipsById", "mindmaps", "narrative", "sequenceOrder", "tags",
            "calendarMarkers", "savedFiltersById", "dependenciesById", "dateConstraintsById", "attachmentsById",
            "timelineRange", "lastTodayDate"})
        self.assertEqual(core["data"]["calendarMarkers"], {"byId": {}, "sortOrder": {}})
        self.assertEqual(core["definitions"]["calendar"]["leapCycles"], [4, 100, 400])
        self.assertEqual(struct.unpack_from("<I", path.read_bytes(), len(path.read_bytes()) - 40)[0], 1)
        result = interop.read_aeon(path)
        names = {item["id"]: item["name"] for item in result["items"]}
        self.assertEqual(set(names.values()), {item.name for item in self.project.items})
        self.assertTrue(all(re.fullmatch(r"[a-zA-Z0-9]{21}", ident) for ident in names))
        for item in result["items"]:
            original = self.project.find(item["name"])
            self.assertEqual(item["summary"], original.body)
            self.assertEqual(item["tags"], original.fields.get("tags", []))
            start, end, _ = item_dates(self.project, original)
            if end == start:
                end = None   # a point's derived end is exported as end == start, which reads back as no end
            for actual, expected in ((item["start"], start), (item["end"], end)):
                if expected is None:
                    self.assertIsNone(actual)
                else:
                    # Aeon carries the nominal year; circa text is preserved as a property.
                    nominal = dates.parse(expected.text.lstrip("~"), self.project.calendars)
                    self.assertEqual(actual, interop.GREGORIAN.format(nominal.lo, nominal.precision))
        roles = {key: spec["label"] for key, spec in result["roles"].items()}
        actual_links = {(names[r["subject"]], roles[r["role"]], names[r["object"]]) for r in result["relationships"]}
        expected_links = {(item.name, role, other.name) for item in self.project.items
                          for role, links in self.project.links(item).items() if role not in interop.DEPENDENCY_KINDS
                          for _, other, _ in links if other}
        self.assertEqual(actual_links, expected_links)
        # Aeon's dependency subject is the predecessor: the flood comes first.
        self.assertEqual({(names[d["subject"]], names[d["object"]], d["kind"]) for d in result["dependencies"]},
                         {("The flood at Saltmarsh", "Crossing Harrow Pass", kind) for kind in interop.DEPENDENCIES})
        self.assertEqual([names[key] for key in result["narrative"]], ["Crossing Harrow Pass", "The flood at Saltmarsh"])
        target = self.empty()
        counts = interop.import_into(target, result)
        self.assertEqual(counts, {"created": len(self.project.items), "skipped": 0, "warnings": []})
        loaded = store.Project(target.root)
        for item in self.project.items:
            imported = loaded.find(item.name)
            self.assertEqual(imported.type, item.type)
            self.assertEqual(imported.body, item.body)
            for actual, expected in zip(item_dates(loaded, imported)[:2], item_dates(self.project, item)[:2]):
                self.assertEqual(actual[:5] if actual else None, expected[:5] if expected else None)
        self.assertEqual(loaded.find("Ivo Brandt").fields["born"], "~1951")
        self.assertEqual([i.name for i in interop._narrative(loaded)], ["Crossing Harrow Pass", "The flood at Saltmarsh"])
        self.assertEqual(set(loaded.links(loaded.find("Crossing Harrow Pass"))) & set(interop.DEPENDENCIES.values()),
                         set(interop.DEPENDENCIES.values()))

    def test_sc3_csv_roundtrip(self):
        path = self.root / "world.csv"
        interop.write_csv(self.project, path)
        self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        header = next(csv.reader(io.StringIO(path.read_text(encoding="utf-8").lstrip("\ufeff"))))
        self.assertEqual(header[:7], interop.CSV_COLUMNS)
        self.assertIn("participants", header)
        self.assertIn("born", header)
        target = self.empty()
        result = interop.import_into(target, interop.read_csv(path))
        self.assertEqual(result["created"], len(self.project.items))
        target = store.Project(target.root)
        for item in self.project.items:
            actual = target.find(item.name)
            self.assertEqual(actual.type, item.type)
            self.assertEqual(actual.body, item.body)
            self.assertEqual(item_dates(target, actual)[:2], item_dates(self.project, item)[:2])
            for role in self.project.links(item):
                self.assertEqual(actual.fields[role], item.fields[role])

    def test_v1_v2_v14_v27_and_date_fields_override_timestamp(self):
        for container_version in (1, 2):
            for file_version in (14, 27):
                with self.subTest(container=container_version, file=file_version):
                    result = self.read_document(sample(file_version), container_version,
                                                [("attachment", "ours.txt", b"our generated content")])
                    self.assertEqual([i["id"] for i in result["items"]], ["c", "b", "a"])
                    self.assertEqual(next(i for i in result["items"] if i["id"] == "a")["start"], "2004-02-29 16:23")
                    self.assertEqual(result["narrative"], ["b", "a"])
                    self.assertEqual(result["attachments"], ["ours.txt"])
                    self.assertEqual({i["id"]: i["parent"] for i in result["items"]}, {"a": "b", "b": None, "c": None})

    def test_invalid_container_and_file_versions(self):
        path = self.root / "invalid.aeon"
        for blob in (b"not an aeon file", b"x" * 100, container(sample())[:-1]):
            path.write_bytes(blob)
            self.assert_invalid(path)
        document = sample()
        document["fileVersion"] = 28
        path.write_bytes(container(document))
        self.assert_invalid(path, "fileVersion")

    def test_bounds_duplicate_entries_and_bad_json(self):
        path = self.root / "invalid.aeon"
        blob = bytearray(container(sample()))
        struct.pack_into("<Q", blob, len(blob) - 32, len(blob) * 2)
        path.write_bytes(blob)
        self.assert_invalid(path, "index")
        blob = bytearray(container(sample()))
        size, = struct.unpack_from("<Q", blob, len(blob) - 32)
        struct.pack_into("<Q", blob, len(blob) - 40 - size, len(blob) * 2)
        path.write_bytes(blob)
        self.assert_invalid(path, "outside")
        path.write_bytes(archive([("", "timeline", archive([])), ("", "timeline", archive([]))], root=True))
        self.assert_invalid(path, "duplicate")
        path.write_bytes(archive([("", "attachments", archive([])),
                                 ("", "timeline", archive([("timeline3.json", "", b"not json")]))], root=True))
        self.assert_invalid(path, "invalid Aeon")

    def test_dates_bc_ad_precision_and_timestamps(self):
        for text, stamp in (("0001-01-01", 0), ("1970-01-01", 62135596800),
                            ("1 BC", -365 * 86400), ("2000-02-29 12:34", 63087424440)):
            with self.subTest(text=text):
                when = interop.GREGORIAN.parse(text)
                encoded = interop._aeon_date(when)
                self.assertEqual(encoded["timestamp"], stamp)
                self.assertEqual(interop.GREGORIAN.parse(interop._date_text(encoded, interop._calendar())).lo, when.lo)
        for precision, text in ((2, "2004"), (3, "2004-02"), (5, "2004-02-29"),
                                (6, "2004-02-29 16:00..2004-02-29 16:59"), (7, "2004-02-29 16:23")):
            doc = sample()
            doc["core"]["data"]["itemDatesById"]["a"]["startDate"]["precision"] = precision
            result = self.read_document(doc)
            self.assertEqual(next(i for i in result["items"] if i["id"] == "a")["start"], text)
        # BC dates finer than a year import in the era form, and export as Aeon's BC era.
        for text, imported, parts in (("March 15, 44 BC", "0044-03-15 BC", (0, 44, 3, 15, 0, 0, 5)),
                                      ("0044-03-15 09:30 BC", "0044-03-15 09:30 BC", (0, 44, 3, 15, 9, 30, 7)),
                                      ("-0043-03", "0044-03 BC", (0, 44, 3, 1, 0, 0, 3))):
            with self.subTest(text=text):
                encoded = interop._aeon_date(interop.GREGORIAN.parse(text))
                self.assertEqual(tuple(encoded[k] for k in ("era", "year", "month", "day", "hour", "minute", "precision")),
                                 parts)
                self.assertEqual(interop._date_text(encoded, interop._calendar()), imported)
                self.assertEqual(interop.GREGORIAN.parse(imported).lo, interop.GREGORIAN.parse(text).lo)

    def test_csv_derived_bc_end_reads_back(self):
        target = self.empty()
        target.create("event", "Ides", {"date": "March 15, 44 BC", "duration": "2d"})
        path = self.root / "bc.csv"
        interop.write_csv(store.Project(target.root), path)
        record = interop.read_csv(path)["items"][0]
        self.assertEqual((record["start"], record["end"]), ("March 15, 44 BC", "0044-03-17 BC"))
        self.assertEqual(interop.GREGORIAN.parse(record["end"]).lo, interop.GREGORIAN.to_axis(-43, 3, 17))

    def test_nesting_imports_as_links_and_exports_back(self):
        doc = sample()   # sample() nests First (a) inside Second (b), both events
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"].update(place={"label": "Location", "category": "LOCATION"},
                                      person={"label": "Person", "category": "PERSON", "canHaveDate": True},
                                      group={"label": "Character Group"})
        for key, type_, label in (("city", "place", "City"), ("inn", "place", "Inn"),
                                  ("ann", "person", "Ann"), ("crew", "group", "Crew")):
            data["itemsById"][key] = {"id": key, "type": type_, "label": label, "tags": {}, "propertyValues": {}}
        data["superAndChildOrderById"].update(city={"super": None, "childOrder": {"inn": 0}},
                                              inn={"super": "city", "childOrder": {}},
                                              crew={"super": None, "childOrder": {"ann": 0}},
                                              ann={"super": "crew", "childOrder": {}})
        target = self.empty()
        self.assertEqual(interop.import_into(target, self.read_document(doc))["warnings"], [])
        loaded = store.Project(target.root)
        self.assertEqual(loaded.find("Inn").fields["located_in"], ["[[City]]"])
        self.assertEqual(loaded.find("Ann").fields["part_of"], ["[[Crew]]"])
        self.assertEqual(loaded.find("First").fields["part_of"], ["[[Second]]"])
        self.assertNotIn("part_of", loaded.find("City").fields)
        self.assertEqual(loaded.config["roles"]["part_of"], {"label": "Part of", "inverse": "Includes", "to": []})
        self.assertEqual([f for f in loaded.findings() if f["code"] in ("ROLE_TYPE", "BROKEN_LINK")], [])
        # Export turns the links back into Aeon nesting, declaring each child type's parent types.
        path = self.root / "nested.aeon"
        interop.write_aeon(loaded, path)
        back = interop.read_aeon(path)
        names = {item["id"]: item["name"] for item in back["items"]}
        self.assertEqual({names[i["id"]]: names.get(i["parent"]) for i in back["items"] if i["parent"]},
                         {"Inn": "City", "Ann": "Crew", "First": "Second"})
        self.assertEqual(back["relationships"], [])
        types = {key: spec["label"] for key, spec in back["types"].items()}
        kinds = {types[i["type"]]: i["type"] for i in back["items"]}
        self.assertEqual({types[t] for t in back["types"][kinds["Character"]]["superTypes"]}, {"Character Group"})
        self.assertEqual({types[t] for t in back["types"][kinds["Location"]]["superTypes"]}, {"Location"})
        # Only a location inside a location is located_in; part_of is declared only when used.
        del data["superAndChildOrderById"]["a"], data["superAndChildOrderById"]["ann"]
        target = self.empty("places")
        interop.import_into(target, self.read_document(doc))
        self.assertNotIn("part_of", store.Project(target.root).config.get("roles", {}))

    def test_nesting_export_never_makes_a_loop(self):
        target = self.empty()
        target.create("event", "A", {"part_of": "[[B]]"})
        target.create("event", "B", {"part_of": "[[A]]"})
        path = self.root / "loop.aeon"
        interop.write_aeon(store.Project(target.root), path)
        parents = {item["name"]: item["parent"] for item in interop.read_aeon(path)["items"]}
        self.assertEqual(sorted(parent is None for parent in parents.values()), [False, True])

    def test_dated_types_keep_their_names(self):
        doc = sample()
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"].update(back={"label": "Backstory", "canHaveDate": True},
                                      task={"label": "Task", "canHaveDate": True},
                                      clue={"label": "Clue", "canHaveDate": False})
        for key, type_ in (("a", "back"), ("b", "task"), ("c", "clue")):
            data["itemsById"][key]["type"] = type_
        data["itemsById"]["d"] = {"id": "d", "type": "ev", "label": "Fourth", "tags": {}, "propertyValues": {}}
        target = self.empty()
        interop.import_into(target, self.read_document(doc))
        loaded = store.Project(target.root)
        self.assertEqual({i.name: i.type for i in loaded.items},
                         {"First": "backstory", "Second": "task", "Third": "clue", "Fourth": "event"})
        self.assertEqual(loaded.config["types"]["backstory"],
                         {"label": "Backstory", "plural": "backstory", "category": "event", "id_prefix": "BACKSTORY"})
        self.assertEqual(loaded.config["types"]["clue"]["category"], "thing")
        self.assertNotIn("event", loaded.config["types"])
        for key, spec in loaded.config["types"].items():
            self.assertTrue(all(spec.get(k) for k in ("label", "plural", "category", "id_prefix")), key)
        self.assertEqual(loaded.find("First").fields["date"], "2004-02-29 16:23")
        path = self.root / "typed.aeon"
        interop.write_aeon(loaded, path)
        back = {spec["label"]: spec["canHaveDate"] for spec in interop.read_aeon(path)["types"].values()}
        self.assertEqual((back["Backstory"], back["Task"], back["Clue"]), (True, True, False))

    def test_multitext_survives_a_round_trip(self):
        doc = sample()
        doc["core"]["definitions"]["properties"]["byId"] = {"m": {"label": "Motivation", "format": "multitext"}}
        text = 'Hiding his past.\nHe says "never".'
        doc["core"]["data"]["itemsById"]["a"]["propertyValues"] = {"m": text}
        target = self.empty()
        interop.import_into(target, self.read_document(doc))
        path = self.root / "multitext.aeon"
        interop.write_aeon(store.Project(target.root), path)
        back = interop.read_aeon(path)
        first = next(i for i in back["items"] if i["name"] == "First")
        self.assertEqual({back["properties"][pid]["label"]: value for pid, value in first["fields"].items()}["motivation"],
                         text)

    def test_import_schema_and_into_and_repeated_import(self):
        doc = sample()
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"].update(person={"label": "Actor", "category": "PERSON"},
                                      place={"label": "Venue", "category": "LOCATION"},
                                      other={"label": "Plot Thread", "canHaveDate": False})
        data["itemsById"]["a"]["type"] = "person"
        data["itemsById"]["b"]["type"] = "place"
        data["itemsById"]["c"]["type"] = "other"
        defs["references"]["byId"] = {"r": {"label": "Visits", "types": {"place": True}}}
        defs["properties"]["byId"] = {"p": {"label": "Motivation", "format": "text"}}
        data["itemsById"]["a"]["propertyValues"] = {"p": "Find the map"}
        data["relationshipsById"] = {"r": {"subject": "a", "reference": "r", "object": "b"}}
        data["dependenciesById"] = {"d": {"subject": "c", "object": "a", "dependencyType": "FS"}}
        target = self.empty(config={"paths": ["Wiki"]})
        result = self.read_document(doc)
        self.assertEqual(interop.import_into(target, result, into="Imported")["created"], 3)
        reloaded = store.Project(target.root)
        self.assertEqual({i.type for i in reloaded.items}, {"character", "location", "plot_thread"})
        self.assertTrue(all(i.path.startswith("Imported/") for i in reloaded.items))
        self.assertEqual(reloaded.find("First").fields["motivation"], "Find the map")
        self.assertEqual(reloaded.links(reloaded.find("First"))["visits"][0][1].name, "Second")
        self.assertIn("visits", reloaded.config["roles"])
        self.assertIn("plot_thread", reloaded.config["types"])
        before = {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()}
        again = interop.import_into(reloaded, result)
        self.assertEqual((again["created"], again["skipped"]), (0, 3))
        self.assertEqual(len(again["warnings"]), 3)
        self.assertEqual(before, {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()})

    def test_csv_custom_properties_and_quoted_unicode(self):
        path = self.root / "custom.csv"
        store.atomic_write(path, '\ufefflabel,type,startDate,summary,tags,custom,ignored\r\n"Café, north",event,2001,"Line one\nLine two","[""red,blue"", ""雪""]",value,no\r\n')
        data = interop.read_csv(path)
        target = self.empty(config={"properties": {"custom": {"format": "text"}}})
        interop.import_into(target, data)
        item = store.Project(target.root).find("Café, north")
        self.assertEqual(item.body, "Line one\nLine two")
        self.assertEqual(item.fields["tags"], ["red,blue", "雪"])
        self.assertEqual(item.fields["custom"], "value")
        self.assertNotIn("ignored", item.fields)

    def test_csv_derived_duration_end(self):
        target = self.empty()
        target.create("event", "Journey", {"date": "2000-01-01 12:00", "duration": "2d"})
        target = store.Project(target.root)
        path = self.root / "duration.csv"
        interop.write_csv(target, path)
        record = interop.read_csv(path)["items"][0]
        self.assertEqual(record["start"], "2000-01-01 12:00")
        self.assertEqual(record["end"], "2000-01-03 12:00")

    def test_csv_malformed_rows_headers_and_encoding(self):
        path = self.root / "bad.csv"
        for content in (b"label,type,type\na,event,event\n", b"name,type\na,event\n",
                        b"label,type\na,event,extra\n", b"label,type\na\n", b"label,type\na,\n",
                        b"label,type\n\xff,event\n"):
            path.write_bytes(content)
            with self.assertRaises(store.LoreError) as caught:
                interop.read_csv(path)
            self.assertEqual(caught.exception.code, "INVALID")

    def test_invalid_date_does_not_read_timestamp(self):
        for change in ({"month": 0}, {"day": 30}, {"era": -1}, {"era": 9}):
            with self.subTest(change=change):
                doc = sample()
                doc["core"]["data"]["itemDatesById"]["a"]["startDate"].update(change)
                with self.assertRaises(store.LoreError) as caught:
                    self.read_document(doc)
                self.assertEqual(caught.exception.code, "INVALID")

    def test_import_duplicate_names_are_suffixed_and_existing_names_skipped(self):
        doc = sample()
        data = doc["core"]["data"]
        data["itemsById"]["d"] = {**copy.deepcopy(data["itemsById"]["c"]), "id": "d"}   # a second "Third"
        doc["core"]["definitions"]["references"]["byId"] = {"r": {"label": "See also", "types": {}}}
        data["relationshipsById"] = {"1": {"subject": "a", "reference": "r", "object": "d"},
                                     "2": {"subject": "b", "reference": "r", "object": "c"}}
        result = self.read_document(doc)
        target = self.empty()
        counts = interop.import_into(target, result)
        self.assertEqual((counts["created"], counts["skipped"]), (4, 0))
        loaded = store.Project(target.root)
        self.assertEqual(loaded.find("First").fields["see_also"], ["[[Third (2)]]"])
        self.assertEqual(loaded.find("Second").fields["see_also"], ["[[Third]]"])
        # Names that already exist in the project are skipped, and their files stay untouched.
        before = {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()}
        again = interop.import_into(loaded, result)
        self.assertEqual((again["created"], again["skipped"]), (0, 4))
        self.assertEqual(before, {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()})

    def test_zero_duration_end_is_not_a_death(self):
        doc = sample()
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"]["person"] = {"label": "Person", "category": "PERSON", "canHaveDate": True}
        data["itemsById"]["b"]["type"] = "person"
        born = {"era": 1, "year": 1771, "month": 5, "day": 1, "precision": 5}
        data["itemDatesById"]["a"]["endDate"] = dict(data["itemDatesById"]["a"]["startDate"])
        data["itemDatesById"]["b"] = {"startDate": born, "endDate": dict(born)}
        data["itemDatesById"]["c"] = {"startDate": born, "endDate": {**born, "day": 2}}
        result = self.read_document(doc)
        ends = {item["name"]: item["end"] for item in result["items"]}
        self.assertEqual(ends, {"First": None, "Second": None, "Third": "1771-05-02"})
        target = self.empty()
        interop.import_into(target, result)
        loaded = store.Project(target.root)
        self.assertEqual(loaded.find("Second").fields["born"], "1771-05-01")
        self.assertNotIn("died", loaded.find("Second").fields)
        self.assertNotIn("end", loaded.find("First").fields)
        self.assertEqual(loaded.find("Third").fields["end"], "1771-05-02")

    def test_dependencies_put_the_successor_after_the_predecessor(self):
        doc = sample()
        data = doc["core"]["data"]
        day = lambda n: {"era": 1, "year": 2000, "month": 1, "day": n, "precision": 5}
        data["itemDatesById"] = {"a": {"startDate": day(1), "endDate": day(3)},
                                 "b": {"startDate": day(2), "endDate": day(5)},
                                 "c": {"startDate": day(6), "endDate": day(7)}}
        # Aeon's subject is the predecessor: Second finishes before Third starts (FS);
        # Second starts and ends no earlier than First (SS, FF), but not at the same moment.
        data["dependenciesById"] = {"fs": {"subject": "b", "object": "c", "dependencyType": "FS"},
                                    "ss": {"subject": "a", "object": "b", "dependencyType": "SS"},
                                    "ff": {"subject": "a", "object": "b", "dependencyType": "FF"}}
        target = self.empty()
        self.assertEqual(interop.import_into(target, self.read_document(doc))["warnings"], [])
        loaded = store.Project(target.root)
        self.assertEqual(loaded.find("Third").fields["after"], ["[[Second]]"])
        second = loaded.find("Second").fields
        self.assertNotIn("after", second)
        self.assertEqual((second["starts_after_start"], second["ends_after_end"]), (["[[First]]"], ["[[First]]"]))
        self.assertNotIn("same_start", second)
        self.assertTrue(loaded.config["roles"]["starts_after_start"]["label"])
        self.assertTrue(loaded.config["roles"]["ends_after_end"]["label"])
        self.assertEqual([f for f in checks.run(loaded) + loaded.findings() if f["code"].startswith("DEPENDENCY")], [])
        path = self.root / "planned.aeon"
        interop.write_aeon(loaded, path)
        back = interop.read_aeon(path)
        names = {item["id"]: item["name"] for item in back["items"]}
        self.assertEqual({(names[d["subject"]], names[d["object"]], d["kind"]) for d in back["dependencies"]},
                         {("Second", "Third", "FS"), ("First", "Second", "SS"), ("First", "Second", "FF")})
        self.assertEqual(back["relationships"], [])

    def test_list_properties_import_option_labels(self):
        doc = sample()
        doc["core"]["definitions"]["properties"]["byId"] = {"g": {"label": "Gender", "format": "list", "allowed": {
            "opt1": {"id": "opt1", "label": "Male"}, "opt2": {"id": "opt2", "label": "Female"}}}}
        doc["core"]["data"]["itemsById"]["a"]["propertyValues"] = {"g": "opt2"}
        result = self.read_document(doc)
        self.assertEqual(next(i for i in result["items"] if i["id"] == "a")["fields"], {"g": "Female"})
        target = self.empty()
        interop.import_into(target, result)
        self.assertEqual(store.Project(target.root).find("First").fields["gender"], "Female")

    def test_unlinkable_name_characters_are_replaced(self):
        doc = sample()
        doc["core"]["data"]["itemsById"]["b"]["label"] = "Modern/International Design"
        target = self.empty()
        counts = interop.import_into(target, self.read_document(doc))
        self.assertEqual(counts["created"], 3)
        self.assertTrue(any("Modern/International Design" in w and "Modern-International Design" in w
                            for w in counts["warnings"]))
        loaded = store.Project(target.root)
        self.assertEqual(loaded.find("Modern-International Design").type, "event")
        self.assertIn("[[Modern-International Design]]", Path(target.root, "narrative.md").read_text(encoding="utf-8"))

    def test_import_indexes_the_project_once(self):
        doc = sample()
        items = doc["core"]["data"]["itemsById"]
        for n in range(30):
            items[f"x{n}"] = {"id": f"x{n}", "type": "ev", "label": f"Extra {n}", "tags": {}, "propertyValues": {}}
        result = self.read_document(doc)
        target = self.empty()
        original = store.Project._index
        with mock.patch.object(store.Project, "_index", autospec=True, side_effect=original) as index:
            self.assertEqual(interop.import_into(target, result)["created"], 33)
        self.assertLessEqual(index.call_count, 3)   # not once per created item

    def test_csv_types_match_the_schema_case_insensitively(self):
        path = self.root / "case.csv"
        store.atomic_write(path, "label,type,startDate,endDate\r\nAda,Character,1815,1852\r\n")
        target = self.empty()
        interop.import_into(target, interop.read_csv(path))
        loaded = store.Project(target.root)
        ada = loaded.find("Ada")
        self.assertEqual(ada.type, "character")
        self.assertEqual((ada.fields["born"], ada.fields["died"]), ("1815", "1852"))
        self.assertNotIn("Character", loaded.config.get("types", {}))

    def test_a_name_that_matches_another_planned_file_stem_is_suffixed(self):
        path = self.root / "stems.csv"
        store.atomic_write(path, "label,type\r\nAcme Inc.,organization\r\nAcme Inc,character\r\n")
        target = self.empty()
        counts = interop.import_into(target, interop.read_csv(path))
        self.assertEqual(counts["created"], 2)
        self.assertEqual({i.name for i in store.Project(target.root).items}, {"Acme Inc.", "Acme Inc (2)"})

    def test_aeon_role_on_builtin_key_adds_its_target_types(self):
        doc = sample()
        defs, data = doc["core"]["definitions"], doc["core"]["data"]
        defs["types"]["byId"]["team"] = {"label": "Team", "canHaveDate": False}
        data["itemsById"]["c"]["type"] = "team"
        defs["references"]["byId"] = {"m": {"label": "Member Of", "types": {"team": True}}}
        data["relationshipsById"] = {"r": {"subject": "a", "reference": "m", "object": "c"}}
        target = self.empty()
        interop.import_into(target, self.read_document(doc))
        loaded = store.Project(target.root)
        self.assertEqual(loaded.schema["roles"]["member_of"]["to"], ["organization", "team"])
        self.assertEqual(loaded.schema["roles"]["member_of"]["label"], "Member of")
        self.assertEqual([f for f in loaded.findings() if f["code"] == "ROLE_TYPE"], [])

    def test_file_name_collisions_are_planned_before_any_write(self):
        doc = sample()
        items = doc["core"]["data"]["itemsById"]
        for key, label in (("a", "Mr."), ("b", "Mr"), ("c", "CON")):
            items[key]["label"] = label
        items["d"] = {"id": "d", "type": "ev", "label": "Stray", "tags": {}, "propertyValues": {}}
        target = self.empty()
        store.atomic_write(Path(target.root, "Events", "stray.md"), "not an item\n")
        counts = interop.import_into(target, self.read_document(doc))
        self.assertEqual(counts["created"], 4)
        loaded = store.Project(target.root)
        # "Mr" is imported first and "Mr." would also be stored as Mr.md; CON keeps its name in CON_.md.
        self.assertEqual({item.name for item in loaded.items}, {"Mr", "Mr. (2)", "CON", "Stray (2)"})
        self.assertEqual(len({item.path.lower() for item in loaded.items}), 4)
        self.assertEqual(Path(target.root, "Events", "stray.md").read_text(encoding="utf-8"), "not an item\n")
        self.assertEqual(interop._suffixed("Con.Air", 2), "Con (2).Air")   # Con.Air.md is also the CON device
        # A destination that cannot be written is refused before lore.json or any item changes.
        target = self.empty("refused", config={"types": {"event": {"label": "Event", "folder": "../outside"}}})
        doc["core"]["definitions"]["types"]["byId"]["other"] = {"label": "Plot Thread", "canHaveDate": False}
        items["d"]["type"] = "other"
        before = {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()}
        with self.assertRaises(store.LoreError):
            interop.import_into(target, self.read_document(doc))
        self.assertEqual(before, {p: p.read_bytes() for p in Path(target.root).rglob("*") if p.is_file()})

    def test_import_refuses_outside_destination_before_writes(self):
        target = self.empty()
        before = Path(target.root, "lore.json").read_bytes()
        with self.assertRaises(store.LoreError):
            interop.import_into(target, self.read_document(sample()), into="../outside")
        self.assertEqual(Path(target.root, "lore.json").read_bytes(), before)

    def test_markdown_chronology_and_fields(self):
        path = self.root / "world.md"
        interop.write_markdown(self.project, path)
        text = path.read_text(encoding="utf-8")
        self.assertLess(text.index("| Ivo Brandt |"), text.index("| Mara Quell |"))
        self.assertLess(text.index("| The flood at Saltmarsh |"), text.index("| Crossing Harrow Pass |"))
        self.assertIn("| Date | Name | Type | Location | Participants |", text)
        self.assertIn("| Saltmarsh | Mara Quell, Ivo Brandt |", text)
        for item in self.project.items:
            self.assertIn(f"## {item.name}", text)
            for key in item.fields:
                self.assertIn(f"**{key}**:", text)
