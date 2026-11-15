#!/usr/bin/env python3
"""Validate ORCT 0.2 datasets: the JSON Schema, then the rules of clauses 6 and 7
the schema can't express (references, parents, row keys, required features).

Usage: validate.py <file or dir> ...   (exit 1 on any error)
"""
import json
import os
import re
import sys
from collections import Counter

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "schema", "orct-0.2.schema.json")) as fh:
    VALIDATOR = jsonschema.Draft202012Validator(json.load(fh))
DECIMAL = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
DURATION = re.compile(r"^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?$")
KEYS = ("object", "entry", "exit", "vehicle_class", "user_class", "time_class", "product", "volume", "priority")


def check(d):
    errs = []

    def unique(items, what):
        seen = set()
        for x in items:
            if x["id"] in seen:
                errs.append(f"duplicate {what} id {x['id']}")
            seen.add(x["id"])
        return seen

    sources = unique(d["sources"], "source")
    sets = d["vehicle_class_sets"]
    class_set = {}
    for s in sets:
        for c in s["classes"]:
            if c["id"] in class_set:
                errs.append(f"duplicate vehicle class id {c['id']}")
            class_set[c["id"]] = s["id"]
    for s in sets:
        by_id = {c["id"]: c for c in s["classes"]}
        for c in s["classes"]:
            if c.get("fallback") and c["fallback"] not in by_id:
                errs.append(f"class {c['id']}: fallback {c['fallback']} is not in its set")
            seen, cur = {c["id"]}, by_id.get(c.get("fallback"))
            while cur:  # 6.6.3: fallbacks shall not form a cycle
                if cur["id"] in seen:
                    errs.append(f"class {c['id']}: fallbacks form a cycle")
                    break
                seen.add(cur["id"])
                cur = by_id.get(cur.get("fallback"))
    every = [x["id"] for k in ("sources", "time_classes", "calendars", "user_classes", "charge_objects", "charges", "rules")
             for x in d.get(k, [])] + [c["id"] for s in sets for c in s["classes"]] + [s["id"] for s in sets]
    errs += [f"id {i} is used more than once in the dataset" for i, n in sorted(Counter(every).items()) if n > 1]
    calendars = unique(d.get("calendars", []), "calendar")
    times = unique(d.get("time_classes", []), "time class")
    for t in d.get("time_classes", []):
        for cal in [c for sel in t.get("days", []) for c in sel.get("calendars", []) + sel.get("exclude", {}).get("calendars", [])]:
            if cal not in calendars:
                errs.append(f"time class {t['id']}: calendar {cal} unknown")
    users = unique(d.get("user_classes", []), "user class")
    objects = {o["id"]: o for o in d["charge_objects"]}
    unique(d["charge_objects"], "charge object")
    state = {}

    def visit(oid):  # depth-first search for unknown parents and cycles
        state[oid] = 1
        for p in objects[oid].get("parents", []):
            if p not in objects:
                errs.append(f"object {oid}: parent {p} unknown")
            elif state.get(p) == 1:
                errs.append(f"object {oid}: parents form a cycle through {p}")
            elif p not in state:
                visit(p)
        state[oid] = 2

    for oid in objects:
        if oid not in state:
            visit(oid)
    charges = {c["id"]: c for c in d["charges"]}
    unique(d["charges"], "charge")
    rules = unique(d.get("rules", []), "rule")

    # A use of an object with several parents must not reach two rows that differ only in their
    # object, through different parents at the same distance (6.10.3).
    multi = [o for o in objects if len(objects[o].get("parents", [])) > 1]
    if multi:
        def dist(oid):
            out, frontier = {oid: 0}, [oid]
            while frontier:
                nxt = []
                for o in frontier:
                    for p in objects.get(o, {}).get("parents", []):
                        if p not in out:
                            out[p] = out[o] + 1
                            nxt.append(p)
                frontier = nxt
            return out
        for c in d["charges"]:
            if "object" not in c["columns"]:
                continue
            oi = c["columns"].index("object")
            groups = {}
            for r in c["rows"]:
                groups.setdefault(tuple(v for i, v in enumerate(r) if i != oi and c["columns"][i] != "amount"), set()).add(r[oi])
            for oid in multi:
                dd = dist(oid)
                for objs in groups.values():
                    reach = [(dd[o], o) for o in objs if o in dd]
                    if reach:
                        m = min(x for x, _ in reach)
                        if len({o for x, o in reach if x == m}) > 1:
                            errs.append(f"charge {c['id']}: object {oid} reaches rows of {sorted(o for x, o in reach if x == m)} at the same distance")

    used = set()
    for c in d["charges"]:
        where = f"charge {c['id']}"
        used.add("type." + c["type"])
        cols = c["columns"]
        errs += [f"{where}: source {s} unknown" for s in c["sources"] if s not in sources]
        if c["type"] == "od":
            if "object" in cols:
                errs.append(f"{where}: an od charge is keyed by entry and exit, not object")
        elif "object" not in cols and not c.get("objects"):
            errs.append(f"{where}: needs an object column or objects")
        elif "entry" in cols or "exit" in cols:
            errs.append(f"{where}: entry and exit are only for od charges")
        hdr = d["dataset"]
        if c.get("valid_from", hdr["valid_from"]) < hdr["valid_from"] or \
                (hdr.get("valid_to") and c.get("valid_to", hdr["valid_to"]) > hdr["valid_to"]):
            errs.append(f"{where}: validity outside the dataset's")
        if "volume" in cols:
            used.add("volume")
            if c["type"] not in ("section", "od", "point", "area"):
                errs.append(f"{where}: volume is only for section, od, point and area charges")
        if c.get("dynamic"):
            used.add("dynamic")
            if not any(x["scope"] == c["id"] and x["status"] == "unpriced" for x in d["coverage"]):
                errs.append(f"{where}: a dynamic charge shall be listed in coverage as unpriced")
        if "product" in cols and c["type"] != "period":
            errs.append(f"{where}: product is only for period charges")
        errs += [f"{where}: object {o} unknown" for o in c.get("objects", []) if o not in objects]
        if c.get("rounding"):
            used.add("rounding")
        seen = set()
        for n, r in enumerate(c["rows"]):
            if len(r) != len(cols):
                errs.append(f"{where} row {n}: {len(r)} values for {len(cols)} columns")
                continue
            row = dict(zip(cols, r))
            if not isinstance(row["amount"], str) or not DECIMAL.match(row["amount"]):
                errs.append(f"{where} row {n}: amount {row['amount']!r} is not a decimal string")
            for k in ("object", "entry", "exit"):
                if row.get(k) is not None and row[k] not in objects:
                    errs.append(f"{where} row {n}: {k} {row[k]} unknown")
            if row.get("vehicle_class") is not None and row["vehicle_class"] not in class_set:
                errs.append(f"{where} row {n}: vehicle class {row['vehicle_class']} unknown")
            if row.get("time_class") is not None:
                used.add("time_classes")
                if row["time_class"] not in times:
                    errs.append(f"{where} row {n}: time class {row['time_class']} unknown")
            if row.get("user_class") is not None:
                used.add("user_classes")
                if row["user_class"] not in users:
                    errs.append(f"{where} row {n}: user class {row['user_class']} unknown")
            if row.get("product") is not None and not DURATION.match(str(row["product"])):
                errs.append(f"{where} row {n}: product {row['product']!r} is not an ISO 8601 duration")
            if row.get("priority") is not None and not isinstance(row["priority"], int):
                errs.append(f"{where} row {n}: priority must be an integer")
            if row.get("volume") is not None and not (isinstance(row["volume"], int) and row["volume"] >= 1):
                errs.append(f"{where} row {n}: volume must be an integer from 1")
            for k in ("object", "entry", "exit", "vehicle_class", "user_class", "time_class", "product"):  # string keys
                if row.get(k) is not None and not isinstance(row[k], str):
                    errs.append(f"{where} row {n}: {k} must be a string or null")
            key = tuple(row.get(k) for k in KEYS)
            if key in seen:
                errs.append(f"{where} row {n}: repeats the keys of an earlier row")
            seen.add(key)
            if len(errs) > 50:
                return errs
    if any(sel.get("calendars") or sel.get("exclude", {}).get("calendars")
           for t in d.get("time_classes", []) for sel in t.get("days", [])):
        used.add("calendars")
    for r in d.get("rules", []):
        used.add("rule." + r["kind"])
        if r["params"].get("time_class"):
            used.add("time_classes")
        if r["params"].get("user_class"):
            used.add("user_classes")
        errs += [f"rule {r['id']}: charge {c} unknown" for c in r["applies_to"] if c not in charges]
        p = r["params"]
        if r["kind"] == "included_in" and charges.get(p.get("charge"), {}).get("type") != "od":
            errs.append(f"rule {r['id']}: included_in needs an od charge")
        for o in ([p["object"]] if "object" in p else []) + p.get("objects", []):
            if o not in objects:
                errs.append(f"rule {r['id']}: object {o} unknown")
        if p.get("time_class") is not None and p["time_class"] not in times:
            errs.append(f"rule {r['id']}: time class {p['time_class']} unknown")
        if p.get("user_class") is not None and p["user_class"] not in users:
            errs.append(f"rule {r['id']}: user class {p['user_class']} unknown")
        for k in ("percent", "factor", "amount"):
            if k in p and not (isinstance(p[k], str) and DECIMAL.match(p[k])):
                errs.append(f"rule {r['id']}: {k} must be a decimal string")

    depth = {"Point": 0, "MultiPoint": 1, "LineString": 1, "MultiLineString": 2, "Polygon": 2, "MultiPolygon": 3}

    def positions(c, n):  # RFC 7946 nesting; yields positions, or None on a bad shape
        if n == 0:
            yield c if isinstance(c, list) and len(c) in (2, 3) and all(isinstance(v, (int, float)) for v in c) else None
        elif not isinstance(c, list) or not c:
            yield None
        else:
            for x in c:
                yield from positions(x, n - 1)

    def geometry_errors(where, g):
        out = []
        pos = list(positions(g["coordinates"], depth[g["type"]]))
        if None in pos:
            return [f"{where}: {g['type']} coordinates are not nested as RFC 7946 says"]
        if any(not (-180 <= x[0] <= 180 and -90 <= x[1] <= 90) for x in pos):
            out.append(f"{where}: a position is outside longitude -180..180, latitude -90..90")
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        if any(len(r) < 4 or r[0] != r[-1] for poly in rings for r in poly):
            out.append(f"{where}: a polygon ring is not closed or has fewer than 4 positions")
        return out
    for oid, o in objects.items():
        for part in ("location", "from", "to"):
            g = (o.get(part) or {}).get("geometry") if part != "location" else o.get("location", {}).get("geometry")
            if g:
                errs += geometry_errors(f"object {oid} {part}", g)
    scopes = {c["scope"] for c in d["coverage"]}
    for oid, o in objects.items():  # 6.9: an unlocated station, point, area or section is in coverage
        located = (o.get("location", {}).get("geometry") if o["type"] in ("station", "point", "area")
                   else (o.get("location", {}).get("geometry")
                         or (o.get("from", {}).get("geometry") and o.get("to", {}).get("geometry")))
                   if o["type"] == "section" else True)
        if not located and oid not in scopes:
            errs.append(f"object {oid}: no location and not in coverage")
    for t in d.get("time_classes", []):
        for a, b in t.get("times", []):
            if a == "24:00":
                errs.append(f"time class {t['id']}: an interval can't start at 24:00")
        for sel in t.get("days", []):
            for part in (sel, sel.get("exclude", {})):
                for a, b in part.get("date_ranges", []):
                    if len(a) != len(b):
                        errs.append(f"time class {t['id']}: date range {a}..{b} mixes MM-DD and YYYY-MM-DD")
                    elif len(a) == 10 and a > b:
                        errs.append(f"time class {t['id']}: date range {a}..{b} ends before it starts")
                for a, b in part.get("easter", []):
                    if a > b:
                        errs.append(f"time class {t['id']}: Easter range {a}..{b} ends before it starts")
        if t.get("defined") is False and t["id"] not in scopes:
            errs.append(f"time class {t['id']}: not defined and not in coverage")
    for cal in d.get("calendars", []):
        if any(x > cal["covers_to"] for x in cal["dates"]):
            errs.append(f"calendar {cal['id']}: dates after covers_to")
    ids = {"dataset"} | set(objects) | set(charges) | rules | times | users | set(class_set) | calendars
    errs += [f"coverage: scope {c['scope']} unknown" for c in d["coverage"] if c["scope"] not in ids]
    missing = used - set(d["dataset"].get("required_features", []))
    if missing:
        errs.append(f"required_features misses {sorted(missing)}")
    if d.get("extensions") and not any(c["status"] != "complete" for c in d["coverage"]):
        pass  # extensions may hold information only; coverage is the producer's statement
    return errs


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
                yield from (os.path.join(root, n) for n in sorted(names) if n.endswith(".orct.json"))
        else:
            yield p


def main():
    bad = n = 0
    for f in files(sys.argv[1:]):
        n += 1
        with open(f) as fh:
            d = json.load(fh)
        errs = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message[:200]}" for e in VALIDATOR.iter_errors(d)]
        if not errs:
            errs = check(d)
        if errs:
            bad += 1
            print(f, *errs[:10], sep="\n  ")
    print(f"{n} files, {bad} invalid")
    sys.exit(1 if bad or not n else 0)


if __name__ == "__main__":
    main()
