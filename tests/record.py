#!/usr/bin/env python3
"""Records the reference calculator's statements for sample usages of every
charge, for comparing another calculator with it (carbon-cost's Go one:
ORCT_RECORDED=<out.jsonl> ORCT_DATA=<dir> go test ./orct -run TestRecordedStatements).

Usage: record.py <dir with .orct.json files> <out.jsonl> [--rows N]

For each charge: up to N of its rows (default 200, spread over the table),
each used by three vehicles, at noon on a weekday and at 23:30 on a Sunday,
paying with and without an electronic device. Each line holds the datasets,
the usage and the statement's completeness, totals, lines (charge, amount,
objects, row) and issue codes.
"""
import glob
import json
import os
import sys
from datetime import date, timedelta
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from orct_calc import calculate  # noqa: E402

VEHICLES = [
    {"train_mass_kg": 40000, "mass_kg": 18000, "train_axles": 5, "axles": 2, "train_length_m": 16.5, "euro_class": "6", "co2_class": 1},
    {"train_mass_kg": 12000, "mass_kg": 12000, "train_axles": 2, "axles": 2, "train_length_m": 10, "euro_class": "5", "co2_class": 1},
    {"train_mass_kg": 26000, "mass_kg": 26000, "train_axles": 3, "axles": 3, "train_length_m": 12, "euro_class": "4", "co2_class": 4},
]


def days(valid_from):
    """A weekday and a Sunday from the dataset's first day."""
    d = date.fromisoformat(valid_from)
    while d.weekday() > 3:
        d += timedelta(days=1)
    s = d + timedelta(days=6 - d.weekday())
    return [d.isoformat() + "T11:00:00Z", s.isoformat() + "T22:30:00Z"]


def usages(d):
    ds = d["dataset"]
    for ch in d["charges"]:
        cols, rows = ch["columns"], ch["rows"]
        n = int(os.environ.get("RECORD_ROWS", "200"))
        pick = rows if len(rows) <= n else [rows[i * len(rows) // n] for i in range(n)]
        uses = []
        for r in pick or [[]]:
            row = dict(zip(cols, r))
            if ch["type"] == "od" and row.get("entry") and row.get("exit"):
                uses.append([(row["entry"], "entry"), (row["exit"], "exit")])
            else:
                objs = [row.get("object")] if row.get("object") else ch.get("objects", [])
                uses.append([(o, None) for o in objs])
        seen = set()
        for use in uses:
            if tuple(use) in seen:
                continue
            seen.add(tuple(use))
            for i, v in enumerate(VEHICLES):
                for j, when in enumerate(days(ds["valid_from"])):
                    events, quants = [], []
                    for k, (o, role) in enumerate(use):
                        e = {"dataset": ds["id"], "object": o, "time": when}
                        if role:
                            e["role"] = role
                        if ch["type"] in ("distance", "section"):
                            e["km"] = "12.5"
                        events.append(e)
                        if ch["type"] == "quantity":
                            quants.append({"dataset": ds["id"], "object": o, "unit": ch["unit"], "value": "2.5", "time": when})
                    u = {"orct_usage": "0.3", "vehicle": v, "payment": ["electronic"] if (i + j) % 2 else [], "events": events}
                    if quants:
                        u["quantities"] = quants
                    yield u


def record(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    out = []
    for u in usages(d):
        st = calculate([d], u)
        out.append(json.dumps({"datasets": [d["dataset"]["id"]], "usage": u,
                               "statement": {"complete": st["complete"], "totals": st["totals"],
                                             "lines": [[l["charge"], l["amount"], l["objects"], l.get("row")] for l in st["lines"]],
                                             "issues": [i["code"] for i in st["issues"]]}}, ensure_ascii=False))
    return out


def main():
    args = sys.argv[1:]
    if "--rows" in args:
        i = args.index("--rows")
        os.environ["RECORD_ROWS"] = args[i + 1]
        del args[i:i + 2]
    src, out = args
    files = sorted(glob.glob(os.path.join(src, "**", "*.orct.json"), recursive=True))
    n = 0
    with open(out, "w", encoding="utf-8") as fh, Pool() as p:
        for lines in p.imap(record, files):
            for line in lines:
                fh.write(line + "\n")
                n += 1
    print(f"{n} usages recorded from {len(files)} datasets")


if __name__ == "__main__":
    main()
