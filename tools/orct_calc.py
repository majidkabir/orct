#!/usr/bin/env python3
"""Reference calculator for ORCT 0.2 (spec clause 8).

Usage: orct_calc.py <usage.json> <dataset.orct.json> ...   prints the charge statement

It favours clarity over speed: every step names the clause it implements.
"""
import calendar
import json
import re
import sys
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, Decimal
from zoneinfo import ZoneInfo

IMPLEMENTED = {"type.distance", "type.section", "type.od", "type.od.chain", "type.point", "type.area", "type.period",
               "type.quantity", "time_classes", "calendars", "user_classes", "rounding", "criteria.any_of", "rule.exemption",
               "rule.included_in", "rule.passage_group", "rule.factor", "rule.discount", "rule.minimum", "rule.cap"}
NULL_RANK = 10 ** 6
MINOR_UNITS = {"JPY": 0, "KRW": 0, "ISK": 0, "CLP": 0, "BHD": 3, "KWD": 3, "OMR": 3, "TND": 3, "JOD": 3}


def fmt(d):
    s = format(d.normalize(), "f") if d == d.to_integral_value() else format(d, "f").rstrip("0")
    return "0" if s in ("-0", "") else s


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


class Unknown(Exception):
    """A value the data or the usage doesn't give (8.9); kind is "vehicle" or "time"."""

    def __init__(self, message, kind="vehicle"):
        super().__init__(message)
        self.kind = kind


class Dataset:
    def __init__(self, doc):
        self.doc = doc
        self.id = doc["dataset"]["id"]
        self.tz = ZoneInfo(doc["dataset"]["timezone"])
        self.currency = doc["dataset"]["currency"]
        self.objects = {o["id"]: o for o in doc["charge_objects"]}
        self._anc = {}
        self.sets = doc["vehicle_class_sets"]
        self.set_of = {c["id"]: s["id"] for s in self.sets for c in s["classes"]}
        self.classes = {c["id"]: c for s in self.sets for c in s["classes"]}
        self.times = {t["id"]: t for t in doc.get("time_classes", [])}
        self.calendars = {c["id"]: c for c in doc.get("calendars", [])}
        self.users = {u["id"]: u for u in doc.get("user_classes", [])}
        self.charges = {c["id"]: c for c in doc["charges"]}
        self.partial = {c["scope"] for c in doc["coverage"] if c["status"] != "complete"}

    def ancestors(self, oid):
        """{object: parent steps} for oid and everything above it, by the shortest path (6.9)."""
        if oid in self._anc:
            return self._anc[oid]
        dist, frontier = {oid: 0}, [oid]
        while frontier:
            nxt = []
            for o in frontier:
                for p in self.objects.get(o, {}).get("parents", []):
                    if p not in dist:
                        dist[p] = dist[o] + 1
                        nxt.append(p)
            frontier = nxt
        self._anc[oid] = dist
        return dist

    def local(self, ts):
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(self.tz)

    # 6.7 time classes --------------------------------------------------------
    def day_in(self, sel, d):
        if "weekdays" in sel and d.isoweekday() not in sel["weekdays"]:
            return False
        if "months" in sel and d.month not in sel["months"]:
            return False
        sets = [k for k in ("dates", "date_ranges", "easter", "calendars") if k in sel]
        if sets:
            md, iso = d.strftime("%m-%d"), d.isoformat()
            hit = any(x == md or x == iso for x in sel.get("dates", []))
            for a, b in sel.get("date_ranges", []):
                if len(a) == 5:
                    hit |= (a <= md <= b) if a <= b else (md >= a or md <= b)
                else:
                    hit |= a <= iso <= b
            for a, b in sel.get("easter", []):
                hit |= a <= (d - easter(d.year)).days <= b
            for cid in sel.get("calendars", []):
                cal = self.calendars[cid]
                if iso > cal["covers_to"]:
                    raise Unknown(f"calendar {cid} is complete only to {cal['covers_to']}", "time")
                hit |= iso in cal["dates"]
            if not hit:
                return False
        return not ("exclude" in sel and self.day_in(sel["exclude"], d))

    def day_selected(self, tc, d):
        return not tc.get("days") or any(self.day_in(s, d) for s in tc["days"])

    def in_time_class(self, tid, t):
        tc = self.times[tid]
        if tc.get("defined") is False:
            raise Unknown(f"time class {tid} is not defined", "time")
        hm = t.strftime("%H:%M")
        if not tc.get("times"):
            return self.day_selected(tc, t.date())
        for start, end in tc["times"]:
            if start < end:
                if start <= hm < end and self.day_selected(tc, t.date()):
                    return True
            else:  # crosses midnight: belongs to the day it starts on
                if hm >= start and self.day_selected(tc, t.date()):
                    return True
                if hm < end and self.day_selected(tc, t.date() - timedelta(days=1)):
                    return True
        return False


# 6.6 vehicle classes --------------------------------------------------------
def meets(criteria, vehicle):
    """True or False; raises Unknown when no condition fails but a tested parameter is missing (6.6.2)."""
    result, missing = _meets(criteria, vehicle)
    if result is None:
        raise Unknown(f"vehicle parameter {missing} is missing", "vehicle")
    return result


def _meets(criteria, vehicle):
    """(True | False | None, a missing parameter): three-valued, None is unknown."""
    missing = None
    for param, cond in criteria.items():
        if param == "any_of":
            results = [_meets(alt, vehicle) for alt in cond]
            if any(r is True for r, _ in results):
                continue
            if all(r is False for r, _ in results):
                return False, None
            missing = missing or next(m for r, m in results if r is None)
            continue
        if param not in vehicle:
            missing = missing or param
            continue
        v = vehicle[param]
        if isinstance(cond, dict):
            if ("min" in cond and v < cond["min"]) or ("max" in cond and v > cond["max"]) or \
               ("gt" in cond and not v > cond["gt"]) or ("lt" in cond and not v < cond["lt"]):
                return False, None
        elif isinstance(cond, list):
            if v not in cond:
                return False, None
        elif v != cond:
            return False, None
    return (None, missing) if missing else (True, None)


def classify(ds, vehicle):
    """The vehicle's class in each set: the first it meets (6.6.3); Unknown recorded per set."""
    out = {}
    for s in ds.sets:
        try:
            out[s["id"]] = next((c["id"] for c in s["classes"] if meets(c["criteria"], vehicle)), None)
        except Unknown as e:
            out[s["id"]] = e
    return out


class Calc:
    def __init__(self, datasets, usage):
        self.ds = {d.id: d for d in datasets}
        self.usage = usage
        self.vehicle = usage.get("vehicle", {})
        self.lines, self.issues = [], []
        self.complete = True

    def issue(self, code, message, ds=None, charge=None):
        self.issues.append({k: v for k, v in {"code": code, "message": message, "dataset": ds, "charge": charge}.items() if v})
        self.complete = False

    def held(self, ds):
        """User classes held: named in the usage, or matched by payment means (6.8)."""
        held = set(self.usage.get("user_classes", {}).get(ds.id, []))
        pay = set(self.usage.get("payment", []))
        held |= {u["id"] for u in ds.users.values() if pay & set(u.get("payment", []))}
        return held

    # 6.10.3 row selection --------------------------------------------------------
    def select(self, ds, ch, use, vclass, held):
        """use: {object|entry|exit, time, product}. Returns (row index, row) or None.

        A row with an unknown key (missing vehicle parameter, undefined time class) is only
        a problem if it would have been selected (8.9): then a missing vehicle parameter
        makes the use unpriced, and an unknown time class makes the result incomplete."""
        cols = ch["columns"]
        cands = []
        for n, r in enumerate(ch["rows"]):
            row = dict(zip(cols, r))
            ranks, unknown, ok = [], None, True
            for c in cols:
                if c in ("amount", "priority"):
                    continue
                v = row.get(c)
                if v is None:
                    ranks.append(NULL_RANK)
                    continue
                rank = None
                if c in ("object", "entry", "exit"):
                    rank = ds.ancestors(use.get(c)).get(v)
                elif c == "vehicle_class":
                    cur = vclass.get(ds.set_of.get(v))
                    if isinstance(cur, Unknown):
                        unknown, rank = unknown or cur, 0
                    else:
                        seen = 0
                        while cur:
                            if cur == v:
                                rank = seen
                                break
                            cur, seen = ds.classes[cur].get("fallback"), seen + 1
                elif c == "time_class":
                    try:
                        rank = 0 if ds.in_time_class(v, use["time"]) else None
                    except Unknown as e:
                        unknown, rank = unknown or e, 0
                elif c == "user_class":
                    rank = 0 if v in held else None
                elif c == "product":
                    rank = 0 if v == use.get("product") else None
                if rank is None:
                    ok = False
                    break
                ranks.append(rank)
            if ok:
                cands.append(((-(row.get("priority") or 0), ranks), n, row, unknown))
        known = sorted((c for c in cands if c[3] is None), key=lambda c: c[0])
        best = None
        if known:
            top = [c for c in known if c[0] == known[0][0]]
            if len(top) > 1 and not all(c[2].get("user_class") for c in top):
                self.issue("ambiguous_rows", f"rows {[c[1] for c in top]} tie", ds.id, ch["id"])
            pick = min(top, key=lambda c: Decimal(c[2]["amount"]))
            best = (pick[1], pick[2])
        for key, n, row, unk in cands:
            if unk is not None and (not known or key <= known[0][0]):
                if unk.kind == "vehicle":
                    raise unk
                self.issue("unknown_time_class", str(unk), ds.id, ch["id"])
                break
        return best

    # 8.4 uses per charge type ------------------------------------------------------
    def charge_objects(self, ds, ch):
        objs = set(ch.get("objects", []))
        for r in ch["rows"]:
            row = dict(zip(ch["columns"], r))
            objs |= {row[k] for k in ("object", "entry", "exit") if row.get(k)}
        return objs

    def uses(self, ds, ch, events):
        objs = self.charge_objects(ds, ch)
        mine = [e for e in events if set(ds.ancestors(e["object"])) & objs]
        t = ch["type"]
        if t in ("distance", "section", "point"):
            out = []
            for e in mine:
                q = Decimal(1)
                if t == "distance":
                    q = Decimal(str(e.get("km", 0)))
                    if ch["unit"] == "tkm":
                        mass = self.vehicle.get(ch.get("mass_basis", "train_mass_kg"))
                        if mass is None:
                            raise Unknown(f"vehicle parameter {ch.get('mass_basis', 'train_mass_kg')} is missing")
                        cap = ch.get("mass_cap_kg") or mass
                        q = q * Decimal(min(mass, cap)) / 1000
                elif t == "section" and ch["unit"] == "km":
                    km = ds.objects[e["object"]].get("length_km")
                    if km is None:
                        raise Unknown(f"section {e['object']} has no official length")
                    q = Decimal(str(km))
                out.append(({"object": e["object"], "time": ds.local(e["time"])}, q, [e["object"]], e))
            return out
        if t == "od":
            return self.od_uses(ds, ch, mine)
        if t == "area":
            if ch["unit"] == "entry":
                return [({"object": e["object"], "time": ds.local(e["time"])}, Decimal(1), [e["object"]], e)
                        for e in mine if e.get("role") == "entry"]
            days = {}
            for e in mine:
                days.setdefault(ds.local(e["time"]).date(), []).append(e)
            return [("day", d, es) for d, es in sorted(days.items())]
        if t == "period":
            if ch.get("day_basis") == "rolling":
                return [("period", sorted({ds.local(e["time"]) for e in mine}), mine)]
            return [("period", sorted({ds.local(e["time"]).date() for e in mine}), mine)]
        if t == "quantity":
            return [({"object": q["object"], "time": ds.local(q["time"])}, Decimal(q["value"]), [q["object"]], q)
                    for q in self.usage.get("quantities", []) if q["dataset"] == ds.id and q["object"] in objs
                    and q["unit"] == ch["unit"]
                    and ch.get("valid_from", "0000") <= ds.local(q["time"]).date().isoformat() <= ch.get("valid_to", "9999-12-31")]
        return []

    def od_uses(self, ds, ch, events):
        events = sorted(events, key=lambda e: e["time"])
        trips, cur = [], []
        for e in events:
            if e.get("role") == "entry" and cur:
                trips.append(cur)
                cur = []
            cur.append(e)
            if e.get("role") == "exit":
                trips.append(cur)
                cur = []
        if cur:
            trips.append(cur)
        out = []
        for trip in trips:
            pairs = [(trip[0], trip[-1])]
            if ch.get("pairing") == "chain":
                pairs, i = [], 0
                while i < len(trip):
                    j = next((j for j in range(len(trip) - 1, i - 1, -1) if self.priced(ds, ch, trip[i], trip[j])), None)
                    if j is None:
                        pairs.append((trip[i], trip[-1]))
                        break
                    pairs.append((trip[i], trip[j]))
                    if j == len(trip) - 1:
                        break
                    i = j
            for a, b in pairs:
                basis = ch.get("time_basis", "entry")
                when = b["time"] if basis == "exit" else a["time"]
                out.append(({"entry": a["object"], "exit": b["object"], "time": ds.local(when),
                             "trip": (a["time"], b["time"])}, Decimal(1), [a["object"], b["object"]], a))
        return out

    def priced(self, ds, ch, a, b):
        use = {"entry": a["object"], "exit": b["object"], "time": ds.local(a["time"])}
        try:
            return self.lookup(ds, ch, use, self._vclass, self._held) is not None
        except Unknown:
            return False

    def lookup(self, ds, ch, use, vclass, held):
        sel = self.select(ds, ch, use, vclass, held)
        if sel is None and ch["type"] == "od" and not ch.get("directed"):
            sel = self.select(ds, ch, {**use, "entry": use["exit"], "exit": use["entry"]}, vclass, held)
        return sel

    # 8 calculation --------------------------------------------------------------------
    def run(self):
        events_by_ds = {}
        for e in self.usage.get("events", []):
            events_by_ds.setdefault(e["dataset"], []).append(e)
        for q in self.usage.get("quantities", []):
            events_by_ds.setdefault(q["dataset"], [])
        for dsid, events in events_by_ds.items():
            ds = self.ds.get(dsid)
            if ds is None:
                self.issue("unknown_dataset", f"dataset {dsid} not given")
                continue
            self.dataset(ds, events)
        return self.statement()

    def dataset(self, ds, events):
        doc = ds.doc
        missing = set(doc["dataset"].get("required_features", [])) - IMPLEMENTED
        if missing:
            self.issue("unsupported_feature", f"{sorted(missing)}", ds.id)
        valid = [e for e in events if doc["dataset"]["valid_from"] <= ds.local(e["time"]).date().isoformat()
                 <= doc["dataset"].get("valid_to", "9999-12-31")]
        if len(valid) < len(events):
            self.issue("outside_validity", f"{len(events) - len(valid)} events outside the dataset's validity", ds.id)
        try:
            if not meets(doc["liable_vehicles"]["criteria"], self.vehicle):
                return
        except Unknown as e:
            self.issue("missing_parameter", str(e), ds.id)
            return
        self._vclass, self._held = classify(ds, self.vehicle), self.held(ds)
        touched = {a for e in valid for a in ds.ancestors(e["object"])}
        rules = doc.get("rules", [])
        lines = []
        for ch in doc["charges"]:
            in_force = [e for e in valid if ch.get("valid_from", "0000") <= ds.local(e["time"]).date().isoformat()
                        <= ch.get("valid_to", "9999-12-31")]
            try:
                mine = self.price_charge(ds, ch, in_force)
            except Unknown as e:
                self.issue("unpriced", str(e), ds.id, ch["id"])
                continue
            lines += self.exempt(ds, ch, rules, mine)
        priced = {l["charge"] for l in lines}
        for scope in sorted(ds.partial & (touched | {"dataset"} | priced)):
            self.issue("partial_coverage", f"coverage of {scope} is partial", ds.id)
        lines = self.apply_rules(ds, rules, lines)
        self.round_lines(ds, lines)
        self.lines += lines

    def line_date(self, ds, l):
        t = l["_event"]["time"]
        return (ds.local(t).date() if "T" in t else date.fromisoformat(t[:10])).isoformat()

    def exempt(self, ds, ch, rules, lines):
        """6.11 exemption: drop the lines of exempt vehicles dated within the rule's dates."""
        for r in rules:
            if r["kind"] != "exemption" or ch["id"] not in r["applies_to"] or not lines:
                continue
            p = r["params"]
            try:
                if not meets(p.get("criteria", {}), self.vehicle):
                    continue
            except Unknown as e:
                self.issue("missing_parameter", str(e), ds.id, ch["id"])
                continue
            lines = [l for l in lines if not p.get("from", "0000") <= self.line_date(ds, l) <= p.get("until", "9999-12-31")]
        return lines

    def line(self, ds, ch, objs, row_n, row, q, event):
        tax = ch.get("tax") or ds.doc["tax"]
        rate = Decimal(row["amount"])
        out = {"dataset": ds.id, "charge": ch["id"], "component": ch["component"], "objects": objs, "row": row_n,
               "quantity": q, "unit": ch["unit"], "rate": rate, "amount": rate * q, "currency": ds.currency,
               "tax_basis": tax["basis"], "sources": ch["sources"], "_event": event}
        if tax.get("rate"):
            out["tax_rate"] = tax["rate"]
        return out

    def price_charge(self, ds, ch, events):
        vclass, held, out = self._vclass, self._held, []
        for u in self.uses(ds, ch, events):
            if u[0] == "day":
                _, d, es = u
                found = None
                for e in es:
                    sel = self.lookup(ds, ch, {"object": e["object"], "time": ds.local(e["time"])}, vclass, held)
                    if sel and (found is None or Decimal(sel[1]["amount"]) > Decimal(found[0][1]["amount"])):
                        found = (sel, e)
                if found:
                    (n, row), e = found
                    out.append(self.line(ds, ch, [e["object"]], n, row, Decimal(1), e))
                elif ch.get("unmatched", "unpriced") == "unpriced":
                    self.issue("unpriced", f"no row for {d}", ds.id, ch["id"])
                continue
            if u[0] == "period":
                out += self.period(ds, ch, u[1], u[2], vclass, held)
                continue
            use, q, objs, event = u
            sel = self.lookup(ds, ch, use, vclass, held)
            if sel is None:
                if ch.get("unmatched", "unpriced") == "unpriced":
                    self.issue("unpriced", f"no row for {objs}", ds.id, ch["id"])
                continue
            line = self.line(ds, ch, objs, sel[0], sel[1], q, event)
            line["_use"] = use
            out.append(line)
        return out

    def period(self, ds, ch, days, events, vclass, held):
        """8.4 period: the cheapest set of products covering every day of use."""
        if not days:
            return []
        products = {}
        for n, r in enumerate(ch["rows"]):
            p = dict(zip(ch["columns"], r)).get("product")
            if p and p not in products:
                length = duration_days(p)
                if length is None:
                    self.issue("unsupported_product", f"product {p}", ds.id, ch["id"])
                    continue
                sel = self.lookup(ds, ch, {"object": events[0]["object"], "time": ds.local(events[0]["time"]), "product": p}, vclass, held)
                if sel:
                    products[p] = (length, sel)
        if not products:
            self.issue("unpriced", "no product priced", ds.id, ch["id"])
            return []
        best = {len(days): (Decimal(0), [])}
        for i in range(len(days) - 1, -1, -1):
            cands = []
            for p, (length, (n, row)) in products.items():
                end = product_end(days[i], p)
                j = next((k for k in range(i, len(days)) if days[k] >= end), len(days))
                cost, buys = best[j]
                cands.append((cost + Decimal(row["amount"]), [(p, n, row, days[i])] + buys))
            best[i] = min(cands, key=lambda x: x[0])
        return [self.line(ds, ch, sorted({e["object"] for e in events}), n, row, Decimal(1), {"time": start.isoformat(), "product": p})
                for p, n, row, start in best[0][1]]

    # 8.6 rules ---------------------------------------------------------------------------
    def apply_rules(self, ds, rules, lines):
        order = ["included_in", "passage_group", "factor", "discount", "minimum", "cap"]
        for kind in order:
            for r in (x for x in rules if x["kind"] == kind):
                lines = getattr(self, "rule_" + kind)(ds, r, lines)
            if kind == "discount":  # percentages add up, then come off once (6.11)
                for l in lines:
                    pct = l.pop("_discount", None)
                    if pct:
                        l["amount"] -= l["amount"] * pct / 100
        for r in rules:
            if r["kind"] not in order + ["exemption"]:
                self.issue("unsupported_rule", r["kind"], ds.id)
        return lines

    def rule_included_in(self, ds, r, lines):
        trips = [tuple(ds.local(x) for x in l["_use"]["trip"]) for l in lines
                 if l["charge"] == r["params"]["charge"] and "_use" in l]
        objs = set(r["params"].get("objects", []))
        keep = []
        for l in lines:
            if l["charge"] in r["applies_to"] and (not objs or set(l["objects"]) & objs):
                t = ds.local(l["_event"]["time"])
                if any(a <= t <= b for a, b in trips):
                    continue
            keep.append(l)
        return keep

    def rule_passage_group(self, ds, r, lines):
        p = r["params"]
        objs, span = set(p["objects"]), timedelta(minutes=p["minutes"])
        group = sorted((l for l in lines if l["charge"] in r["applies_to"] and set(l["objects"]) & objs and l["amount"] > 0),
                       key=lambda l: l["_event"]["time"])
        run_start, run = None, []
        for l in group + [None]:
            t = ds.local(l["_event"]["time"]) if l else None
            if l is None or run_start is None or t - run_start >= span:
                if run:
                    keep = run[0] if p.get("pays", "first") == "first" else max(run, key=lambda x: x["amount"])
                    for x in run:
                        if x is not keep:
                            x["amount"] = Decimal(0)
                            x.setdefault("notes", []).append(f"passage group {r['id']}")
                run, run_start = [], t
            if l:
                run.append(l)
        return lines

    def rule_factor(self, ds, r, lines):
        p = r["params"]
        f = Decimal(p["factor"])
        for l in lines:
            if l["charge"] in r["applies_to"] and l["unit"] in ("km", "tkm"):
                okm = Decimal(str(l["_event"].get("overlays", {}).get(p["object"], 0)))
                if okm:
                    share = okm / Decimal(str(l["_event"]["km"]))
                    l["amount"] += l["amount"] * share * (f - 1)
                    l.setdefault("notes", []).append(f"factor {p['factor']} on {okm} km")
        return lines

    def rule_discount(self, ds, r, lines):
        p = r["params"]
        if not any(l["charge"] in r["applies_to"] for l in lines):
            return lines
        try:
            if p.get("criteria") and not meets(p["criteria"], self.vehicle):
                return lines
        except Unknown as e:
            self.issue("missing_parameter", str(e), ds.id)
            return lines
        if p.get("payment") and not set(p["payment"]) & set(self.usage.get("payment", [])):
            return lines
        if p.get("user_class") and p["user_class"] not in self._held:
            return lines
        for l in lines:
            if l["charge"] in r["applies_to"]:
                l["_discount"] = l.get("_discount", Decimal(0)) + Decimal(p["percent"])
                l.setdefault("notes", []).append(f"discount {p.get('name', r['id'])} {p['percent']}%")
        return lines

    def periods(self, ds, r, lines):
        per = r["params"]["per"]
        groups = {}
        for l in lines:
            if l["charge"] not in r["applies_to"]:
                continue
            t = ds.local(l["_event"]["time"]) if "T" in l["_event"]["time"] else datetime.fromisoformat(l["_event"]["time"])
            key = t.date() if per == "day" else (t.year, t.month) if per == "month" else "trip"
            groups.setdefault(key, []).append(l)
        return groups

    def adjustment(self, ds, r, amount, group, note):
        """A line of its own (9.2), on the first charge of the rule's applies_to among the lines it adjusts."""
        charge = next(c for c in r["applies_to"] if any(l["charge"] == c for l in group))
        sample = next(l for l in group if l["charge"] == charge)
        return {**{k: sample[k] for k in ("dataset", "currency", "tax_basis", "sources")}, "charge": charge,
                "component": sample["component"], "objects": [], "quantity": Decimal(1), "unit": "rule",
                "amount": amount, "notes": [note], "_event": sample["_event"]}

    def rule_minimum(self, ds, r, lines):
        for key, group in self.periods(ds, r, lines).items():
            total = sum(l["amount"] for l in group)
            m = Decimal(r["params"]["amount"])
            if total < m:
                lines.append(self.adjustment(ds, r, m - total, group, f"minimum {r['id']}"))
        return lines

    def rule_cap(self, ds, r, lines):
        tc = r["params"].get("time_class")
        cap = Decimal(r["params"]["amount"])
        for key, group in self.periods(ds, r, lines).items():
            if tc:
                try:
                    group = [l for l in group if ds.in_time_class(tc, ds.local(l["_event"]["time"]))]
                except Unknown as e:
                    self.issue("unknown_time_class", str(e), ds.id)
                    continue
            total = sum(l["amount"] for l in group)
            if group and total > cap:
                lines.append(self.adjustment(ds, r, cap - total, group, f"cap {r['id']}"))
        return lines

    # 8.7 rounding ------------------------------------------------------------------------
    def round_lines(self, ds, lines):
        for ch in ds.doc["charges"]:
            rd = ch.get("rounding")
            if not rd:
                continue
            mine = [l for l in lines if l["charge"] == ch["id"]]
            if rd["stage"] == "line":
                for l in mine:
                    l["amount"] = quantize(l["amount"], rd)
            elif rd["stage"] == "charge" and mine:
                total = sum(l["amount"] for l in mine)
                diff = quantize(total, rd) - total
                if diff:
                    lines.append(self.adjustment(ds, {"applies_to": [ch["id"]]}, diff, mine, "rounding"))
            elif rd["stage"] == "statement":
                self._statement_rounding = rd

    def statement(self):
        totals = {}
        for l in self.lines:
            totals[l["currency"]] = totals.get(l["currency"], Decimal(0)) + l["amount"]
        rd = getattr(self, "_statement_rounding", None)
        out_totals = []
        for cur, amt in sorted(totals.items()):
            r = rd or {"increment": "1" if MINOR_UNITS.get(cur, 2) == 0 else "0." + "0" * (MINOR_UNITS.get(cur, 2) - 1) + "1",
                       "mode": "half_up"}
            out_totals.append({"currency": cur, "amount": format(quantize(amt, r), "f")})
        lines = []
        for l in self.lines:
            x = {k: v for k, v in l.items() if not k.startswith("_")}
            for k in ("quantity", "rate", "amount"):
                if k in x:
                    x[k] = fmt(x[k])
            lines.append(x)
        return {"orct_statement": "0.2", "complete": self.complete, "lines": lines, "totals": out_totals,
                "issues": self.issues}


DURATION = re.compile(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?")


def duration_days(p):
    """A product's duration as (years, months, days), or None if it isn't PnYnMnWnD."""
    m = DURATION.fullmatch(p)
    if not m or not any(m.groups()):
        return None
    y, mo, w, d = (int(x or 0) for x in m.groups())
    return y, mo, w * 7 + d


def product_end(start, p):
    """8.4: the first instant (or date) a product bought at start no longer covers. Months and years end
    on the same day of the month, or on the month's last day if it has no such day."""
    y, mo, d = duration_days(p)
    months = start.month - 1 + mo + 12 * y
    year, month = start.year + months // 12, months % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return start.replace(year=year, month=month, day=min(start.day, last)) + timedelta(days=d)


MODES = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN, "up": ROUND_UP, "down": ROUND_DOWN,
         "ceiling": ROUND_CEILING, "floor": ROUND_FLOOR}


def quantize(amount, rd):
    inc = Decimal(rd["increment"])
    return ((amount / inc).quantize(Decimal(1), rounding=MODES[rd["mode"]]) * inc).quantize(inc)


def calculate(datasets, usage):
    return Calc([Dataset(d) for d in datasets], usage).run()


def main():
    usage = json.load(open(sys.argv[1]))
    docs = [json.load(open(p)) for p in sys.argv[2:]]
    print(json.dumps(calculate(docs, usage), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
