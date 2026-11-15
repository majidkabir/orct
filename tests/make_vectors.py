import json, os
SYN = "tests/fixtures/synthetic.orct.json"
SID = "orct-tests/synthetic/2026-01-01"
V40 = {"train_mass_kg": 40000, "train_axles": 5, "euro_class": "6", "co2_class": 1}
V7 = {"train_mass_kg": 7500, "train_axles": 2, "euro_class": "6", "co2_class": 1}
def ev(obj, time, **kw): return {"dataset": SID, "object": obj, "time": time, **kw}
def usage(vehicle, events=(), **kw): return {"orct_usage": "0.2", "vehicle": vehicle, "events": list(events), **kw}
def tot(x): return [{"currency": "EUR", "amount": x}] if x is not None else []
V = []
def add(name, desc, clauses, ds, u, total, complete=True, lines=None):
    exp = {"complete": complete, "totals": tot(total)}
    if lines is not None: exp["lines"] = [{"charge": c, "amount": a} for c, a in lines]
    V.append((name, {"description": desc, "clauses": clauses, "datasets": ds, "usage": u, "expected": exp}))
M = "2026-11-16T10:00:00+01:00"  # a Monday
add("distance-classes", "Per-km rate by mass class; an operator's own row beats the network row (object column, ancestor rank).",
    ["6.10.3", "8.4"], [SYN], usage(V40, [ev("mw", M, km=100), ev("op-x", M, km=10)]), "28.00", lines=[("dist", "25"), ("dist", "3")])
add("distance-exemption", "An exemption rule removes the charge for zero-emission vehicles.", ["6.11", "8.6"], [SYN],
    usage({**V40, "co2_class": 5}, [ev("mw", M, km=100)]), None, lines=[])
add("distance-factor", "A factor rule raises the rate on km the usage attributes to an overlay stretch.", ["6.11", "8.6"], [SYN],
    usage(V40, [ev("mw", M, km=100, overlays={"stretch": 20})]), "27.50")
add("distance-tkm-cap", "Per tonne-km with the mass capped at 40 t.", ["6.10.2", "8.4"], [SYN],
    usage({**V40, "train_mass_kg": 44000}, [ev("alp", M, km=100)]), "91.20")
OD = lambda a, b, t1="2026-11-16T10:00:00+01:00", t2="2026-11-16T11:00:00+01:00": [ev(a, t1, role="entry"), ev(b, t2, role="exit")]
add("od-fallback", "Closed system: the Euro VI class has no row of its own and falls back to its 5-axle class.", ["6.6.3", "6.10.3"], [SYN],
    usage(V40, OD("st-a", "st-b")), "10.00")
add("od-reverse", "A pair without a row in this direction uses the other direction's (directed: false).", ["6.10.2", "8.4"], [SYN],
    usage(V40, OD("st-b", "st-a")), "10.00")
add("od-user-before-time", "At night with electronic payment: the user_class column comes before time_class, so the electronic row (9.50) wins; less the 20% electronic discount, 7.60.",
    ["6.10.3"], [SYN], usage(V40, OD("st-a", "st-b", "2026-11-16T23:00:00+01:00", "2026-11-17T00:30:00+01:00"), payment=["electronic"]), "7.60")
add("od-night", "Entry at night without electronic payment: the night row; the time class is read at entry (time_basis).",
    ["6.7", "6.10.1"], [SYN], usage(V40, OD("st-a", "st-b", "2026-11-16T23:00:00+01:00", "2026-11-17T00:30:00+01:00")), "5.00")
add("od-light", "A light vehicle falls to the catch-all group B.", ["6.6.3"], [SYN], usage(V7, OD("st-a", "st-b")), "4.00")
add("od-discount-rounding", "Discounts of 10% (CO2 class 4) and 20% (electronic) add up to 30%: 9.50 less 30% is 6.65, rounded per line to 0.10 half up: 6.70. (Applied one after the other they would give 6.84, rounded 6.80.)",
    ["6.11", "8.6", "8.7"], [SYN], usage({**V40, "co2_class": 4}, OD("st-a", "st-b"), payment=["electronic"]), "6.70")
add("od-chain", "Chain pairing: from C1 the farthest priced station is C3 (20), then C3 to C4 (6).", ["8.4"], [SYN],
    usage(V40, [ev("c1", "2026-11-16T10:00:00+01:00", role="entry"), ev("c2", "2026-11-16T10:20:00+01:00", role="pass"),
                ev("c3", "2026-11-16T10:40:00+01:00", role="pass"), ev("c4", "2026-11-16T11:00:00+01:00", role="exit")]),
    "26.00", lines=[("odc", "20"), ("odc", "6")])
add("point-priority", "On Sunday the priority row (free) beats the class row.", ["6.10.3"], [SYN],
    usage(V40, [ev("gate", "2026-11-15T10:00:00+01:00")]), "0.00")
add("point-passage-group", "Two passages within 60 minutes pay once (pays: first).", ["6.11", "8.6"], [SYN],
    usage(V40, [ev("gate", M), ev("gate", "2026-11-16T10:30:00+01:00")]), "8.40")
add("point-catch-all", "A class without its own row uses the row with any class.", ["6.10.3"], [SYN],
    usage({"train_mass_kg": 15000, "train_axles": 3, "euro_class": "6", "co2_class": 1}, [ev("gate", M)]), "6.00")
add("point-season-cap", "Two passages in July at the high-season rate (25 each) are capped at 30 a day.", ["6.7", "6.11"], [SYN],
    usage(V40, [ev("bridge", "2026-07-15T10:00:00+02:00"), ev("bridge", "2026-07-15T14:00:00+02:00")]), "30.00")
add("point-undefined-time-class", "A row needs a time class the source doesn't define: priced at the default row, but incomplete.",
    ["6.7", "8.9"], [SYN], usage(V40, [ev("toll3", M)]), "5.00", complete=False)
add("section-minimum", "Section fee 12.00, per-km 0.10 x 12.5 km = 1.25 raised to the 2.00 minimum.", ["6.10.2", "6.11"], [SYN],
    usage(V40, [ev("sec1", M)]), "14.00")
add("area-day", "Zone charged once per weekday in charging hours; not on a public holiday or a Saturday.", ["6.7", "8.4"], [SYN],
    usage(V40, [ev("city", "2026-11-16T08:00:00+01:00"), ev("city", "2026-11-16T17:00:00+01:00"),
                ev("city", "2026-12-25T10:00:00+01:00"), ev("city", "2026-11-21T10:00:00+01:00")]), "15.00")
add("period-days", "Three days of use in a week: three day products (36) are cheaper than a week (40).", ["8.4"], [SYN],
    usage(V40, [ev("vnet", f"2026-11-{d}T10:00:00+01:00") for d in (16, 18, 20)]), "36.00")
add("period-week", "Four days of use: one week product (40) is cheaper than four days (48).", ["8.4"], [SYN],
    usage(V40, [ev("vnet", f"2026-11-{d}T10:00:00+01:00") for d in (16, 17, 18, 19)]), "40.00")
add("quantity", "2.5 t CO2 at 55.50 a tonne.", ["8.4"], [SYN],
    usage(V40, quantities=[{"dataset": SID, "object": "country", "unit": "t_co2", "value": "2.5", "time": M}]), "138.75")
add("included-in", "A bridge passage during a closed-system trip is included in the trip's ticket.", ["6.11"], [SYN],
    usage(V40, OD("st-a", "st-b") + [ev("bridge", "2026-11-16T10:30:00+01:00")]), "10.00")
add("missing-parameter", "The vehicle has no axle count, which the classes test: unpriced, never guessed.", ["6.6.2", "8.9"], [SYN],
    usage({"train_mass_kg": 40000}, [ev("gate", M)]), None, complete=False)
add("outside-validity", "An event after the dataset's validity is not priced.", ["8.2"], [SYN],
    usage(V40, [ev("gate", "2028-01-05T10:00:00+01:00")]), None, complete=False)

CAS = "data/carbon-cost/it/it-cas-2026-01-01.orct.json"; CASID = "carbon-cost/it-cas/2026-01-01"
def cas(a, b, vehicle, pair=True):
    t = "2026-11-20T10:00:00+01:00"
    evs = [{"dataset": CASID, "object": a, "time": t, "role": "entry"}]
    if pair: evs.append({"dataset": CASID, "object": b, "time": "2026-11-20T11:00:00+01:00", "role": "exit"})
    return usage(vehicle, evs)
src = "Official amount from the CAS 2026 tariff, as carbon-cost's TestSicilyCAS asserts it."
add("it-cas-a18", "A18 Messina Sud to Catania Nord, class 5: 10.90. " + src, ["8.4"], [CAS],
    cas("st1:Messina Sud > Roccalumera", "st1:Acireale > Catania Nord", V40), "10.90")
add("it-cas-a18-barrier", "A18 Roccalumera to Taormina (an open barrier, priced from itself to itself): 2.50. " + src, ["8.4"], [CAS],
    cas("st1:Roccalumera > Taormina", None, V40, pair=False), "2.50")
add("it-cas-a20", "A20 Messina Nord to Buonfornello, class 5: 25.40. " + src, ["8.4"], [CAS],
    cas("st2:Messina Nord > Rometta", "st2:Cefalu' > Buonfornello", V40), "25.40")
add("it-cas-a20-light", "Same trip, class B: 10.60. " + src, ["8.4"], [CAS],
    cas("st2:Messina Nord > Rometta", "st2:Cefalu' > Buonfornello", V7), "10.60")
MIL = "data/carbon-cost/it/it-barriers-2026-01-01.orct.json"; MID = "carbon-cost/it-barriers/2026-01-01"
src = "Official 2026 barrier tariff, as carbon-cost's TestMilanBarriers asserts it."
for name, pt, veh, want in (("terrazzano", "pt1", V40, "8.40"), ("terrazzano-light", "pt1", V7, "3.60"),
                            ("vimercate", "pt2", V40, "4.90"), ("sesto", "pt3", V40, "6.30")):
    add(f"it-milan-{name}", f"Milan ring road barrier {name}: {want}. " + src, ["8.4"], [MIL],
        usage(veh, [{"dataset": MID, "object": pt, "time": "2026-11-20T10:00:00+01:00"}]), want)
DE = "data/carbon-cost/de/de-2024-07-01.orct.json"; DEID = "carbon-cost/de/2024-07-01"
src = "Sum of the BFStrMG Anlage 1 parts over 100 km, as carbon-cost's TestGermanyTotals asserts them."
for name, veh, want in (("40t-euro6-co2-1", V40, "34.80"), ("40t-euro5", {**V40, "euro_class": "5"}, "38.90"),
                        ("40t-co2-4", {**V40, "co2_class": 4}, "26.90"), ("7t", {**V7, "train_mass_kg": 7000}, "15.10")):
    add(f"de-{name}", f"German HGV toll, {name}, 100 km: {want}. " + src, ["8.4"], [DE],
        usage(veh, [{"dataset": DEID, "object": "roads", "time": "2026-11-03T10:00:00+01:00", "km": 100}]), want)
for i, (name, v) in enumerate(V, 1):
    with open(f"tests/vectors/{i:03d}-{name}.json", "w") as fh:
        json.dump(v, fh, indent=1, ensure_ascii=False); fh.write("\n")
print(len(V), "vectors")
