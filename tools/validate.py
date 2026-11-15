#!/usr/bin/env python3
"""Validate ORCT datasets: the JSON Schema, then every id they refer to.

Usage: validate.py <file or dir> ...   (exit 1 on any error)
"""
import json
import os
import sys

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "schema", "orct-0.1.schema.json")) as fh:
    VALIDATOR = jsonschema.Draft202012Validator(json.load(fh))


def refs(d):
    errs = []

    def ids(items, what):
        seen = set()
        for x in items:
            if x["id"] in seen:
                errs.append(f"duplicate {what} id {x['id']}")
            seen.add(x["id"])
        return seen

    src, cls = ids(d["sources"], "source"), ids(d["classes"], "class")
    net, chg = ids(d["network"], "network"), ids(d["charges"], "charge")
    for c in d["classes"]:
        if c.get("fallback") and c["fallback"] not in cls:
            errs.append(f"class {c['id']}: fallback {c['fallback']} unknown")
    for c in d["charges"]:
        where = f"charge {c['id']}"
        errs += [f"{where}: source {s} unknown" for s in c["sources"] if s not in src]
        errs += [f"{where}: network {n} unknown" for n in c["applies_to"] + c.get("excludes", []) if n not in net]
        errs += [f"{where}: class {k} unknown" for k in c["rates"] if k not in cls]
        for p in c.get("pairs", []):
            errs += [f"{where}: station {s} unknown" for s in (p["entry"], p["exit"]) if s not in net]
            errs += [f"{where}: class {k} unknown" for k in p["rates"] if k not in cls]
    for m in d.get("modifiers", []):
        errs += [f"modifier {m['kind']}: charge {c} unknown" for c in m["applies_to"] if c not in chg]
        p = m["params"]
        if m["kind"] == "included_in" and p.get("charge") not in chg:
            errs.append(f"modifier included_in: charge {p.get('charge')} unknown")
        if m["kind"] == "factor" and p.get("stretch") not in net:
            errs.append(f"modifier factor: stretch {p.get('stretch')} unknown")
    for c in d["coverage"]:
        if c["scope"] != "dataset" and c["scope"] not in net | chg:
            errs.append(f"coverage: scope {c['scope']} unknown")
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
        errs = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in VALIDATOR.iter_errors(d)]
        if not errs:
            errs = refs(d)
        if errs:
            bad += 1
            print(f, *errs[:10], sep="\n  ")
    print(f"{n} files, {bad} invalid")
    sys.exit(1 if bad or not n else 0)


if __name__ == "__main__":
    main()
