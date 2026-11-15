#!/usr/bin/env python3
"""Compare the ORCT conversion with carbon-cost's own engine, case by case.

Usage: check_oracle.py <oracle.jsonl> <converted dir> [--every N]

Each line of oracle.jsonl (tools/oracle/main.go) is one priced case from
carbon-cost: a truck on a table's rows, a toll point passage, a closed-system
trip, a section, or a zone visit. This prices the same case from the ORCT
dataset with the reference calculator and reports every difference. Exit 1
on any. --every N checks every N-th case only (for a quick run).
"""
import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orct_calc import Calc, Dataset  # noqa: E402

# carbon-cost rounds a discounted closed-system price to the cent; where a source gives prices to more
# decimals ORCT keeps the exact discounted amount (see convert_system). Differences up to half a cent are
# expected there, and only there.
CENT_TOLERANCE = {"es-basque-2026-01-01.json"}
DATA = {}


def load(out_dir):
    index = json.load(open(os.path.join(out_dir, "index.json")))
    for d in index["datasets"]:
        DATA[d["file"].split("/")[1].replace(".orct.json", ".json")] = os.path.join(out_dir, d["file"])


_cache = {}


def dataset(file):
    if file not in _cache:
        _cache[file] = Dataset(json.load(open(DATA[file])))
    return _cache[file]


def vehicle(t):
    return {"train_mass_kg": t["Mass"], "train_axles": t["Axles"], "axles": t["Motor"], "euro_class": str(t["Euro"]),
            "co2_class": t["CO2"], "train_length_m": t["Length"]}


def at(ds, date, hm="12:00", plus=0):
    d = datetime.fromisoformat(f"{date}T{hm}:00").replace(tzinfo=ds.tz) + timedelta(minutes=plus)
    return d.isoformat()


_decided = {}


def decided(ds):
    """The dataset without the rows that need an undefined time class (rush hours carbon-cost lacks)."""
    if ds.id not in _decided:
        doc = json.loads(json.dumps(ds.doc))
        undefined = {t["id"] for t in doc.get("time_classes", []) if t.get("defined") is False}
        for ch in doc["charges"]:
            if "time_class" in ch["columns"]:
                i = ch["columns"].index("time_class")
                ch["rows"] = [r for r in ch["rows"] if r[i] not in undefined]
        _decided[ds.id] = Dataset(doc)
    return _decided[ds.id]


def price(ds, veh, events, payment=()):
    """The statement; where a row needs an undefined time class, ORCT leaves the use unpriced (spec 6.10.3)
    while carbon-cost prices the time the source gives. The incomplete statement is checked, then the
    amounts are compared without those rows."""
    usage = {"orct_usage": "0.2", "vehicle": veh, "payment": list(payment),
             "events": [{"dataset": ds.id, **e} for e in events]}
    st = Calc([ds], usage).run()
    if any(i["code"] == "unknown_time_class" for i in st["issues"]) and \
            any(t.get("defined") is False for t in ds.doc.get("time_classes", [])):
        assert not st["complete"]
        st = Calc([decided(ds)], usage).run()
    return st


def total(st, pred):
    return sum((Decimal(l["amount"]) for l in st["lines"] if pred(l)), Decimal(0))


def same(a, b, tol=Decimal(0)):
    return abs(Decimal(repr(a)) - b) <= tol + Decimal("0.0000001")


def check(case):
    k, f = case["kind"], case["file"]
    ds = dataset(f)
    if k == "rows":
        veh = vehicle(case["truck"])
        road, op = case["road"], case["op"]
        base = "op:" + op if op else ("road:" + road if road else "roads")
        want = {}
        for r in case["rates"] or []:
            want.setdefault(r["area"], {})[r["component"]] = r["per_km"]
        errs = []
        for area in sorted(set(want) | {""}):
            obj = base if not area else (f"{base}:{area}" if road else f"road:{area}")
            if obj not in ds.objects:
                if want.get(area):
                    errs.append(f"no object {obj}")
                continue
            st = price(ds, veh, [{"object": obj, "time": at(ds, case["date"]), "km": 1}])
            got = {}
            for l in st["lines"]:
                if l["charge"] in ds.charges and ds.charges[l["charge"]]["type"] in ("distance", "period") \
                        and l["charge"] != "env_zone_surcharge":
                    got[l["charge"]] = got.get(l["charge"], Decimal(0)) + Decimal(l["amount"])
            # A cell in an area also reaches the components without areas, through its road type.
            exp = {**want.get("", {}), **want.get(area, {})} if case["liable"] and not case["exempt"] else {}
            if set(got) != set(exp) or any(not same(exp[c], got[c]) for c in exp):
                errs.append(f"{obj}: carbon-cost {exp}, ORCT {dict((c, str(v)) for c, v in got.items())} {st['issues'][:2]}")
        return errs
    if k == "envzone":
        st = price(ds, vehicle(case["truck"]), [{"object": "env-zones", "time": at(ds, case["date"]), "km": 1}])
        got = total(st, lambda l: l["charge"] == "env_zone_surcharge")
        return [] if same(case["per_km"], got) else [f"env zone carbon-cost {case['per_km']}, ORCT {got}"]
    if k == "point":
        obj = f"pt{case['j']}"
        st = price(ds, vehicle(case["truck"]), [{"object": obj, "time": at(ds, case["date"], case["time"])}],
                   ["electronic"] if case["etc"] else [])
        got = total(st, lambda l: obj in l["objects"])
        if isinstance(case["amount"], str):
            return [f"oracle error {case['amount']}"]
        return [] if same(case["amount"], got) else [f"{obj} {case['date']} {case['time']} etc={case['etc']}: carbon-cost {case['amount']}, ORCT {got} {st['issues'][:2]}"]
    if k == "group":
        objs = {f"pt{j}" for j, _ in case["passes"]}
        st = price(ds, vehicle(case["truck"]), [{"object": f"pt{j}", "time": at(ds, case["date"], hm)} for j, hm in case["passes"]])
        got = total(st, lambda l: objs & set(l["objects"]))
        return [] if same(case["amount"], got) else [f"{case['passes']} {case['date']}: carbon-cost {case['amount']}, ORCT {got} {st['issues'][:2]}"]
    if k == "congestion":
        st = price(ds, vehicle({"Mass": 40000, "Axles": 5, "Motor": 2, "Euro": 6, "CO2": 1, "Length": 16.5}),
                   [{"object": f"pt{j}", "time": at(ds, case["date"], hm)} for j, hm in case["passes"]])
        got = total(st, lambda l: l["charge"].startswith("congestion"))
        if isinstance(case["amount"], str):
            return [f"oracle error {case['amount']}"]
        if not st["complete"] or not same(case["amount"], got):
            return [f"{case['passes']} {case['date']}: carbon-cost {case['amount']}, ORCT {got} {st['issues'][:2]}"]
        return []
    if k == "system":
        i = case["i"]
        a, b = f"st{i}:{case['entry']}", f"st{i}:{case['exit']}"
        st = price(ds, vehicle(case["truck"]), [{"object": a, "time": at(ds, case["date"], case["time"]), "role": "entry"},
                                                {"object": b, "time": at(ds, case["date"], case["time"], 30), "role": "exit"}],
                   ["electronic"] if case["etc"] else [])
        mine = [l for l in st["lines"] if l["charge"] == f"system{i}"]
        got = total(st, lambda l: l["charge"] == f"system{i}")
        if case["amount"] is None:
            return [] if not mine else [f"{a}->{b}: carbon-cost no price, ORCT {got}"]
        tol = Decimal("0.005") if f in CENT_TOLERANCE else Decimal(0)
        if not same(case["amount"], got, tol) or (case["amount"] and not mine):
            return [f"{a}->{b} {case['time']} etc={case['etc']}: carbon-cost {case['amount']}, ORCT {got} {st['issues'][:2]}"]
        return []
    if k in ("section", "section_km"):
        obj = "sec:" + case["id"]
        hm = "23:00" if case.get("night") else "12:00"
        st = price(ds, vehicle(case["truck"]), [{"object": obj, "time": at(ds, case["date"], hm)}])
        if k == "section":
            got = total(st, lambda l: ds.charges[l["charge"]]["type"] == "section" and ds.charges[l["charge"]]["unit"] == "use")
            return [] if same(case["amount"], got) else [f"{obj} night={case.get('night')}: carbon-cost {case['amount']}, ORCT {got}"]
        got = [l for l in st["lines"] if l["charge"] == "km-" + case["component"]]
        if case["amount"] is None:
            return [] if not got else [f"{obj} {case['component']}: carbon-cost none, ORCT {got[0]['amount']}"]
        g = sum((Decimal(l["amount"]) for l in got), Decimal(0))
        return [] if same(case["amount"], g) else [f"{obj} {case['component']}: carbon-cost {case['amount']}, ORCT {g}"]
    if k == "zone":
        veh = {"train_mass_kg": case["mass"], "euro_class": str(case["euro"])}
        st = price(ds, veh, [{"object": "zone", "time": at(ds, case["date"], case["time"])}])
        got = total(st, lambda l: l["charge"] == "zone-charge")
        return [] if same(case["amount"], got) else [f"zone {case['date']} {case['time']} euro {case['euro']} {case['mass']} kg: carbon-cost {case['amount']}, ORCT {got} {st['issues'][:2]}"]
    return [f"unknown kind {k}"]


def run(chunk):
    out = []
    for line in chunk:
        case = json.loads(line)
        try:
            errs = check(case)
        except Exception as e:  # noqa: BLE001
            errs = [f"{type(e).__name__}: {e}"]
        out += [f"{case['file']} {case['kind']}: {e}" for e in errs]
    return len(chunk), out


def main():
    args = sys.argv[1:]
    every = 1
    if "--every" in args:
        i = args.index("--every")
        every = int(args[i + 1])
        del args[i:i + 2]
    oracle, out_dir = args
    load(out_dir)
    lines = [l for n, l in enumerate(open(oracle)) if n % every == 0]
    chunks = [lines[i:i + 2000] for i in range(0, len(lines), 2000)]
    n, errs = 0, []
    with Pool(initializer=load, initargs=(out_dir,)) as pool:
        for k, e in pool.imap_unordered(run, chunks):
            n += k
            errs += e
    by = {}
    for e in errs:
        key = " ".join(e.split(" ")[:2])
        by.setdefault(key, []).append(e)
    for key, es in sorted(by.items()):
        print(f"{key}: {len(es)} differences, e.g.")
        for e in es[:3]:
            print("   ", e[:400])
    print(f"{n} cases, {len(errs)} differences")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
