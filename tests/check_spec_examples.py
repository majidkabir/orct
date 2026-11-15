#!/usr/bin/env python3
"""Check the examples of the specification's Annex D.

Each JSON block after a `<!-- example: KIND -->` marker is checked: a dataset
against the dataset schema and the validator, a usage against the usage
schema, a charge against the schema's charge definition, and a statement
against the statement schema and against what the reference calculator
computes from the dataset and usage before it.

Usage: check_spec_examples.py [spec.md]   (exit 1 on any error)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import jsonschema  # noqa: E402
from orct_calc import calculate  # noqa: E402
from validate import check  # noqa: E402


def schema(name):
    return json.load(open(os.path.join(ROOT, "schema", name)))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec", "orct-0.2.md")
    text = open(path, encoding="utf-8").read()
    blocks = re.findall(r"<!-- example: (\w+) -->\s*```json\n(.*?)\n```", text, re.S)
    ds_schema = schema("orct-0.2.schema.json")
    validators = {
        "dataset": jsonschema.Draft202012Validator(ds_schema),
        "usage": jsonschema.Draft202012Validator(schema("orct-usage-0.2.schema.json")),
        "statement": jsonschema.Draft202012Validator(schema("orct-statement-0.2.schema.json")),
        "charge": jsonschema.Draft202012Validator({**ds_schema["$defs"]["charge"], "$defs": ds_schema["$defs"]}),
    }
    errs, dataset, usage = [], None, None
    for n, (kind, body) in enumerate(blocks, 1):
        where = f"example {n} ({kind})"
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as e:
            errs.append(f"{where}: not JSON: {e}")
            continue
        errs += [f"{where}: {e.message}" for e in validators[kind].iter_errors(doc)]
        if kind == "dataset":
            errs += [f"{where}: {e}" for e in check(doc)]
            dataset = doc
        elif kind == "usage":
            usage = doc
        elif kind == "statement":
            if dataset is None or usage is None:
                errs.append(f"{where}: no dataset and usage before it")
            elif calculate([dataset], usage) != doc:
                errs.append(f"{where}: differs from what the reference calculator computes:\n"
                            + json.dumps(calculate([dataset], usage), indent=1))
    for e in errs:
        print(e)
    print(f"{len(blocks)} examples, {len(errs)} errors")
    sys.exit(1 if errs or not blocks else 0)


if __name__ == "__main__":
    main()
