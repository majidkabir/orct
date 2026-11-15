#!/usr/bin/env python3
"""Run the conformance vectors against a calculator (spec 4.4).

Usage: run_vectors.py [vector files...]   default: tests/vectors/*.json, with tools/orct_calc.py

A vector passes when the calculator's statement is valid against the statement
schema and has the expected `complete` flag, the expected totals, and, when the
vector lists them, the expected lines (charge and amount, compared as decimals)
and issue codes.
"""
import glob
import json
import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import jsonschema  # noqa: E402
from orct_calc import calculate  # noqa: E402

STATEMENT = jsonschema.Draft202012Validator(json.load(open(os.path.join(ROOT, "schema", "orct-statement-0.2.schema.json"))))
USAGE = jsonschema.Draft202012Validator(json.load(open(os.path.join(ROOT, "schema", "orct-usage-0.2.schema.json"))))


def run(path):
    v = json.load(open(path))
    errs = [e.message for e in USAGE.iter_errors(v["usage"])]
    if errs:
        return [f"usage invalid: {errs[0]}"]
    docs = [json.load(open(os.path.join(ROOT, p))) for p in v["datasets"]]
    st = calculate(docs, v["usage"])
    errs = [f"statement invalid: {e.message}" for e in STATEMENT.iter_errors(st)]
    exp = v["expected"]
    if st["complete"] != exp["complete"]:
        errs.append(f"complete {st['complete']}, want {exp['complete']} (issues {st['issues']})")
    got = {t["currency"]: Decimal(t["amount"]) for t in st["totals"]}
    want = {t["currency"]: Decimal(t["amount"]) for t in exp["totals"]}
    if got != want:
        errs.append(f"totals {got}, want {want}")
    missing = set(exp.get("issues", [])) - {i["code"] for i in st["issues"]}
    if missing:
        errs.append(f"issue codes {sorted(missing)} missing (issues {st['issues']})")
    if "lines" in exp:
        g = sorted((l["charge"], Decimal(l["amount"])) for l in st["lines"])
        w = sorted((l["charge"], Decimal(l["amount"])) for l in exp["lines"])
        if g != w:
            errs.append(f"lines {g}, want {w}")
    return errs


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "tests", "vectors", "*.json")))
    bad = 0
    for p in paths:
        errs = run(p)
        print(("FAIL " if errs else "ok   ") + os.path.basename(p))
        for e in errs:
            print("     " + e)
        bad += bool(errs)
    print(f"{len(paths) - bad}/{len(paths)} vectors pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
