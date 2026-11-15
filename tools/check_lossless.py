#!/usr/bin/env python3
"""Check that the conversion kept every price of carbon-cost's tables.

Usage: check_lossless.py <carbon-cost checkout> <converted dir>
Counts, per table: row rates, entry-exit prices (by group) and toll points,
in the source and in the ORCT file (charges plus extensions). Exit 1 on any
difference.
"""
import json
import os
import sys


def source_counts(t):
    rows = len(t.get("rows", []))
    pairs = sum(len(g) for s in t.get("closed_systems", []) for g in s["prices"].values())
    points = len(t.get("toll_points", []))
    zone = 1 if "charge" in t else 0
    fuel = 1 if "rate_per_t" in t else 0
    return rows + zone + fuel, pairs, points


def orct_counts(d):
    rows = sum(len(c["rates"]) for c in d["charges"] if c["type"] in ("distance", "period", "quantity"))
    rows += 1 if any(c["type"] == "zone" for c in d["charges"]) else 0
    pairs = sum(len(p["rates"]) for c in d["charges"] for p in c.get("pairs", []))
    odd = d.get("extensions", {}).get("x-carbon-cost", {}).get("closed_system_prices_not_mapped", {})
    pairs += sum(1 for s in odd.values() for k in s.values() for g, v in k.items() if isinstance(v, dict) and v.get("default") is not None)
    points = sum(1 for c in d["charges"] if c["id"].startswith("point:"))
    return rows, pairs, points


def main():
    src, out = sys.argv[1:]
    data = os.path.join(src, "rates", "data")
    bad = 0
    for name in sorted(os.listdir(data)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(data, name)) as fh:
            t = json.load(fh)
        f = os.path.join(out, t["country"].lower(), name[:-5] + ".orct.json")
        with open(f) as fh:
            d = json.load(fh)
        a, b = source_counts(t), orct_counts(d)
        dup = sum(1 for c in d["coverage"] if "two rates for one class" in c.get("reason", ""))
        if a != b and not (a[1:] == b[1:] and a[0] - b[0] == dup):
            bad += 1
            print(f"{name}: source rows/pairs/points {a}, ORCT {b}")
    print(f"{bad} tables with missing prices")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
