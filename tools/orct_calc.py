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
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, Decimal
from zoneinfo import ZoneInfo

IMPLEMENTED = {"type.distance", "type.section", "type.od", "type.point", "type.area", "type.period", "type.quantity",
               "time_classes", "calendars", "user_classes", "rounding", "volume", "dynamic", "rule.exemption",
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
    """Something the data or the usage does not decide (8.9). code is the issue code of 9.2."""

    def __init__(self, message, code="missing_parameter"):
        super().__init__(message)
        self.code = code


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
        """True, False, or None when it needs a calendar past its covers_to (6.7, three-valued)."""
        if "weekdays" in sel and d.isoweekday() not in sel["weekdays"]:
            return False
        if "months" in sel and d.month not in sel["months"]:
            return False
        result = True
        if any(k in sel for k in ("dates", "date_ranges", "easter", "calendars")):
            md, iso = d.strftime("%m-%d"), d.isoformat()
            hit = any(x == md or x == iso for x in sel.get("dates", []))
            for a, b in sel.get("date_ranges", []):
                if len(a) == 5:
                    hit = hit or ((a <= md <= b) if a <= b else (md >= a or md <= b))
                else:
                    hit = hit or a <= iso <= b
            for a, b in sel.get("easter", []):
                hit = hit or a <= (d - easter(d.year)).days <= b
            unknown = False
            for cid in sel.get("calendars", []):
                cal = self.calendars[cid]
                if iso > cal["covers_to"]:
                    unknown = True
                else:
                    hit = hit or iso in cal["dates"]
            result = True if hit else (None if unknown else False)
        if result is False or "exclude" not in sel:
            return result
        ex = self.day_in(sel["exclude"], d)
        if ex is True:
            return False
        return None if ex is None else result

    def day_selected(self, tc, d):
        if not tc.get("days"):
            return True
        results = [self.day_in(s, d) for s in tc["days"]]
        if True in results:
            return True
        if None in results:
            raise Unknown(f"time class {tc['id']} needs a calendar past its covers_to for {d}", "unknown_time_class")
        return False

    def in_time_class(self, tid, t):
        tc = self.times[tid]
        if tc.get("defined") is False:
            raise Unknown(f"time class {tid} is not defined", "unknown_time_class")
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
        raise Unknown(f"vehicle parameter {missing} is missing", "missing_parameter")
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
        """use: {object|entry|exit, time, product}. Returns (row index, row), or None when no row matches.

        Raises Unknown when a row whose key can't be decided (a missing vehicle parameter, an undefined
        time class, a calendar past its covers_to) would rank at or above the best decided row, or when
        the best rows tie (6.10.3): the use is then unpriced, never guessed."""
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
                elif c == "volume":
                    nth = use.get("ordinal")
                    if isinstance(nth, Unknown):
                        unknown, rank = unknown or nth, 0
                    elif nth is None or not isinstance(v, int) or v > nth:
                        rank = None
                    else:
                        rank = nth - v
                if rank is None:
                    ok = False
                    break
                ranks.append(rank)
            if ok:
                cands.append(((-(row.get("priority") or 0), ranks), n, row, unknown))
        known = sorted((c for c in cands if c[3] is None), key=lambda c: c[0])
        for key, n, row, unk in cands:
            if unk is not None and (not known or key <= known[0][0]):
                raise unk
        if not known:
            return None
        top = [c for c in known if c[0] == known[0][0]]
        if len(top) > 1:
            others = {tuple((k, v) for k, v in c[2].items() if k not in ("user_class", "amount")) for c in top}
            if len(others) > 1:
                raise Unknown(f"rows {[c[1] for c in top]} tie", "ambiguous_rows")
        pick = min(top, key=lambda c: (Decimal(c[2]["amount"]), c[1]))
        return pick[1], pick[2]

    # 8.4 uses per charge type ------------------------------------------------------
    def charge_objects(self, ds, ch):
        objs = set(ch.get("objects", []))
        for r in ch["rows"]:
            row = dict(zip(ch["columns"], r))
            objs |= {row[k] for k in ("object", "entry", "exit") if row.get(k)}
        return objs

    def uses(self, ds, ch, events):
        """The uses of a charge (8.4): (use, quantity, objects, event), or ("day"/"period", ...) groups."""
        objs = self.charge_objects(ds, ch)
        mine = [e for e in events if set(ds.ancestors(e["object"])) & objs]
        t = ch["type"]
        if t in ("distance", "section", "point"):
            out = []
            for e in mine:
                q = Decimal(1)
                if t == "distance":
                    if e.get("km") is None:
                        out.append(Unknown(f"event on {e['object']} at {e['time']} has no km", "missing_km"))
                        continue
                    q = Decimal(str(e["km"]))
                    if ch["unit"] == "tkm":
                        basis = ch.get("mass_basis", "train_mass_kg")
                        mass = self.vehicle.get(basis)
                        if mass is None:
                            raise Unknown(f"vehicle parameter {basis} is missing", "missing_parameter")
                        cap = ch.get("mass_cap_kg") or mass
                        q = q * Decimal(min(mass, cap)) / 1000
                elif t == "section" and ch["unit"] == "km":
                    km = ds.objects[e["object"]].get("length_km")
                    if km is None:
                        raise Unknown(f"section {e['object']} has no official length", "unpriced")
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
                    for q in self._quantities if q["object"] in objs and q["unit"] == ch["unit"]
                    and ch.get("valid_from", "0000") <= ds.local(q["time"]).date().isoformat() <= ch.get("valid_to", "9999-12-31")]
        return []

    def od_uses(self, ds, ch, events):
        """8.4 od: the events form trips from entry to exit; a trip is priced from its first station to its last."""
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
            a, b = trip[0], trip[-1]
            when = b["time"] if ch.get("time_basis", "entry") == "exit" else a["time"]
            out.append(({"entry": a["object"], "exit": b["object"], "time": ds.local(when),
                         "trip": (a["time"], b["time"])}, Decimal(1), [a["object"], b["object"]],
                        b if ch.get("time_basis") == "exit" else a))
        return out

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
        known = [e for e in events if e["object"] in ds.objects]
        quantities = [q for q in self.usage.get("quantities", []) if q["dataset"] == ds.id and q["object"] in ds.objects]
        for x in [e for e in events if e["object"] not in ds.objects] + \
                 [q for q in self.usage.get("quantities", []) if q["dataset"] == ds.id and q["object"] not in ds.objects]:
            self.issue("unknown_object", f"object {x['object']} is not in the dataset", ds.id)

        def in_validity(x):
            return doc["dataset"]["valid_from"] <= ds.local(x["time"]).date().isoformat() <= doc["dataset"].get("valid_to", "9999-12-31")
        valid, self._quantities = [e for e in known if in_validity(e)], [q for q in quantities if in_validity(q)]
        outside = len(known) - len(valid) + len(quantities) - len(self._quantities)
        if outside:
            self.issue("outside_validity", f"{outside} events or quantities outside the dataset's validity", ds.id)
        try:
            if not meets(doc["liable_vehicles"]["criteria"], self.vehicle):
                return
        except Unknown as e:
            self.issue(e.code, str(e), ds.id)
            return
        self._vclass, self._held = classify(ds, self.vehicle), self.held(ds)
        rules = doc.get("rules", [])
        lines, used = [], set()
        for ch in doc["charges"]:
            in_force = [e for e in valid if ch.get("valid_from", "0000") <= ds.local(e["time"]).date().isoformat()
                        <= ch.get("valid_to", "9999-12-31")]
            try:
                mine = self.price_charge(ds, ch, in_force, used)
            except Unknown as e:
                self.issue(e.code, str(e), ds.id, ch["id"])
                used.add(ch["id"])
                continue
            lines += self.exempt(ds, ch, rules, mine)
        # 8.9: the coverage scopes the usage touches
        touched = {"dataset"} | {a for e in valid + self._quantities for a in ds.ancestors(e["object"])} | used
        touched |= {c for c in self._vclass.values() if isinstance(c, str)} | self._held
        for l in lines:
            row = dict(zip(ds.charges[l["charge"]]["columns"], ds.charges[l["charge"]]["rows"][l["row"]])) if "row" in l else {}
            touched |= {row[k] for k in ("vehicle_class", "time_class", "user_class") if row.get(k)}
        touched |= {r["id"] for r in rules if set(r["applies_to"]) & used}
        for scope in sorted(ds.partial & touched):
            self.issue("partial_coverage", f"coverage of {scope} is not complete", ds.id)
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
            if p.get("user_class") and p["user_class"] not in self._held:
                continue
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
               "quantity": q, "unit": ch["unit"], "rate": row["amount"], "amount": rate * q, "currency": ds.currency,
               "tax_basis": tax["basis"], "basis": ch["basis"], "sources": ch["sources"], "_event": event}
        if ds.doc["dataset"].get("version"):
            out["dataset_version"] = ds.doc["dataset"]["version"]
        rd = ch.get("rounding")
        if rd and rd["stage"] == "use":
            out["amount"] = quantize(out["amount"], rd)
        if tax.get("rate"):
            out["tax_rate"] = tax["rate"]
        return out

    def price_charge(self, ds, ch, events, used):
        """8.5: one line per priced use; an undecided or unmatched use is reported and left out."""
        vclass, held, out = self._vclass, self._held, []
        uses = self.uses(ds, ch, events)
        if ch.get("dynamic"):
            if uses:
                used.add(ch["id"])
                self.issue("dynamic_tariff", f"amounts are set in real time: {ch['dynamic'].get('url', '')}", ds.id, ch["id"])
            return []
        if "volume" in ch["columns"]:
            self.ordinals(ds, ch, uses)

        def unpriced(code, message):
            if code != "unmatched" or ch.get("unmatched", "unpriced") == "unpriced":
                self.issue("unpriced" if code == "unmatched" else code, message, ds.id, ch["id"])

        for u in uses:
            used.add(ch["id"])
            if isinstance(u, Unknown):
                unpriced(u.code, str(u))
                continue
            if u[0] == "day":
                _, d, es = u
                try:
                    found = None
                    for e in es:
                        sel = self.lookup(ds, ch, {"object": e["object"], "time": ds.local(e["time"])}, vclass, held)
                        if sel and (found is None or Decimal(sel[1]["amount"]) > Decimal(found[0][1]["amount"])):
                            found = (sel, e)
                except Unknown as e:
                    unpriced(e.code, f"{d}: {e}")
                    continue
                if found:
                    (n, row), e = found
                    out.append(self.line(ds, ch, [e["object"]], n, row, Decimal(1), e))
                else:
                    unpriced("unmatched", f"no row for {d}")
                continue
            if u[0] == "period":
                try:
                    out += self.period(ds, ch, u[1], u[2], vclass, held)
                except Unknown as e:
                    unpriced(e.code, str(e))
                continue
            use, q, objs, event = u
            try:
                sel = self.lookup(ds, ch, use, vclass, held)
            except Unknown as e:
                unpriced(e.code, f"{objs}: {e}")
                continue
            if sel is None:
                unpriced("unmatched", f"no row for {objs}")
                continue
            line = self.line(ds, ch, objs, sel[0], sel[1], q, event)
            line["_use"] = use
            out.append(line)
        return out

    def ordinals(self, ds, ch, uses):
        """6.10.3 volume: each use's place among the user's uses of the charge in its period, counting the
        prior uses the usage gives for the period of its first use."""
        simple = sorted((u for u in uses if isinstance(u, tuple) and isinstance(u[0], dict)), key=lambda u: u[0]["time"])
        if not simple:
            return
        per = ch["volume"]["per"]

        def period(t):
            return t.year if per == "year" else (t.year, t.month) if per == "month" else t.date()
        prior = self.usage.get("prior_uses", {}).get(ds.id, {}).get(ch["id"])
        first, counts = period(simple[0][0]["time"]), {}
        for u in simple:
            p = period(u[0]["time"])
            counts[p] = counts.get(p, 0) + 1
            if p == first and prior is None:
                u[0]["ordinal"] = Unknown(f"the usage does not give the prior uses of {ch['id']}", "missing_count")
            else:
                u[0]["ordinal"] = (prior if p == first else 0) + counts[p]

    def period(self, ds, ch, days, events, vclass, held):
        """8.4 period: the set of products with the lowest total covering every day (or instant) of use;
        among equal totals the fewest products, then the earliest rows. A product's price is the row
        selected for it at its start."""
        if not days:
            return []
        products = []
        for r in ch["rows"]:
            p = dict(zip(ch["columns"], r)).get("product")
            if p and p not in products:
                if duration_days(p) is None:
                    self.issue("unsupported_product", f"product {p}", ds.id, ch["id"])
                    continue
                products.append(p)
        obj = events[0]["object"]
        objs = sorted({e["object"] for e in events})

        def at(start):
            return start if isinstance(start, datetime) else datetime.combine(start, datetime.min.time(), ds.tz)
        best = {len(days): (Decimal(0), 0, [], [])}
        for i in range(len(days) - 1, -1, -1):
            cands = []
            for p in products:
                sel = self.lookup(ds, ch, {"object": obj, "time": at(days[i]), "product": p}, vclass, held)
                if sel is None:
                    continue
                n, row = sel
                end = product_end(days[i], p)
                j = next((k for k in range(i, len(days)) if days[k] >= end), len(days))
                if j not in best:
                    continue
                cost, count, order, buys = best[j]
                cands.append((cost + Decimal(row["amount"]), count + 1, [n] + order, [(p, n, row, days[i])] + buys))
            if cands:
                best[i] = min(cands, key=lambda x: x[:3])
        if 0 not in best:
            raise Unknown(f"no product priced for {days[0]}", "unpriced")
        return [self.line(ds, ch, objs, n, row, Decimal(1), {"time": at(start).isoformat(), "product": p})
                for p, n, row, start in best[0][3]]

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
                        l["amount"] -= l["amount"] * min(pct, Decimal(100)) / 100
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
            key = t.date() if per == "day" else (t.year, t.month) if per == "month" else "usage"
            groups.setdefault(key, []).append(l)
        return groups

    def adjustment(self, ds, r, amount, group, note):
        """A line of its own (9.2), on the first charge of the rule's applies_to among the lines it adjusts."""
        charge = next(c for c in r["applies_to"] if any(l["charge"] == c for l in group))
        sample = next(l for l in group if l["charge"] == charge)
        return {**{k: sample[k] for k in ("dataset", "dataset_version", "currency", "tax_basis", "basis", "sources") if k in sample},
                "charge": charge,
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
            if rd["stage"] == "use":
                continue
            if rd["stage"] == "line":
                for l in mine:
                    l["amount"] = quantize(l["amount"], rd)
            elif rd["stage"] == "charge" and mine:
                total = sum(l["amount"] for l in mine)
                diff = quantize(total, rd) - total
                if diff:
                    lines.append(self.adjustment(ds, {"applies_to": [ch["id"]]}, diff, mine, "rounding"))

    def statement(self):
        totals = {}
        for l in self.lines:
            totals[l["currency"]] = totals.get(l["currency"], Decimal(0)) + l["amount"]
        out_totals = []
        for cur, amt in sorted(totals.items()):
            r = {"increment": "1" if MINOR_UNITS.get(cur, 2) == 0 else "0." + "0" * (MINOR_UNITS.get(cur, 2) - 1) + "1",
                 "mode": "half_up"}
            out_totals.append({"currency": cur, "amount": format(quantize(amt, r), "f")})
        lines = []
        for l in self.lines:
            x = {k: v for k, v in l.items() if not k.startswith("_")}
            for k in ("quantity", "amount"):
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


MODES = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN, "up": ROUND_UP, "down": ROUND_DOWN}


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
