#!/usr/bin/env python3
"""Smoke test: price one use of an object of every charge in every dataset; the
calculator must return a valid statement without crashing.

Usage: smoke.py <dir with .orct.json files>
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import jsonschema  # noqa: E402
from orct_calc import calculate  # noqa: E402

STATEMENT = jsonschema.Draft202012Validator(json.load(open(os.path.join(ROOT, "schema", "orct-statement-0.2.schema.json"))))
VEHICLE = {"train_mass_kg": 40000, "mass_kg": 18000, "train_axles": 5, "axles": 2, "train_length_m": 16.5,
           "euro_class": "6", "co2_class": 1, "energy": "diesel", "category": "N3", "trailer": True}


def main():
    bad = n = 0
    for f in sorted(glob.glob(os.path.join(sys.argv[1], "**", "*.orct.json"), recursive=True)):
        d = json.load(open(f))
        ds = d["dataset"]
        when = ds["valid_from"] + "T12:00:00Z"
        for ch in d["charges"]:
            cols = ch["columns"]
            row = dict(zip(cols, ch["rows"][0])) if ch["rows"] else {}
            objs = [row.get(k) for k in ("object", "entry", "exit") if row.get(k)] or ch.get("objects", [])
            usage = {"orct_usage": "0.2", "vehicle": VEHICLE, "payment": ["electronic"],
                     "events": [{"dataset": ds["id"], "object": o, "time": when, "km": 10} for o in objs]}
            if ch["type"] == "quantity":
                usage["quantities"] = [{"dataset": ds["id"], "object": o, "unit": ch["unit"], "value": "1", "time": when} for o in objs]
            n += 1
            try:
                st = calculate([d], usage)
                errs = list(STATEMENT.iter_errors(st))
                if errs:
                    raise ValueError(errs[0].message)
            except Exception as e:  # noqa: BLE001
                bad += 1
                print(f"{f} {ch['id']}: {type(e).__name__}: {e}")
    print(f"{n} charges priced, {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
