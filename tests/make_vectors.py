import glob
import json
import os
SYN = "tests/fixtures/synthetic.orct.json"
SID = "orct-tests/synthetic/2026-01-01"
V40 = {"train_mass_kg": 40000, "train_axles": 5, "euro_class": "6", "co2_class": 1}
V7 = {"train_mass_kg": 7500, "train_axles": 2, "euro_class": "6", "co2_class": 1}
def ev(obj, time, **kw): return {"dataset": SID, "object": obj, "time": time, **kw}
def usage(vehicle, events=(), **kw): return {"orct_usage": "0.3", "vehicle": vehicle, "events": list(events), **kw}
def tot(x, cur="EUR"): return [{"currency": cur, "amount": x}] if x is not None else []
V = []
def add(name, desc, clauses, ds, u, total, complete=True, lines=None, issues=None, currency="EUR"):
    exp = {"complete": complete, "totals": tot(total, currency)}
    if lines is not None: exp["lines"] = [{"charge": c, "amount": a} for c, a in lines]
    if issues is not None: exp["issues"] = issues
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
add("od-two-systems", "Two closed systems meet at C3: the trip pays C1 to C3 in the first (20) and C3 to C4 in the second (6).", ["8.4"], [SYN],
    usage(V40, [ev("c1", "2026-11-16T10:00:00+01:00", role="entry"), ev("c2", "2026-11-16T10:20:00+01:00", role="pass"),
                ev("c3", "2026-11-16T10:40:00+01:00", role="pass"), ev("c4", "2026-11-16T11:00:00+01:00", role="exit")]),
    "26.00", lines=[("odc", "20.00"), ("odc2", "6.00")])
add("point-priority", "On Sunday the priority row (free) beats the class row.", ["6.10.3"], [SYN],
    usage(V40, [ev("gate", "2026-11-15T10:00:00+01:00")]), "0.00")
add("point-passage-group", "Two passages within 60 minutes pay once (pays: first).", ["6.11", "8.6"], [SYN],
    usage(V40, [ev("gate", M), ev("gate", "2026-11-16T10:30:00+01:00")]), "8.40")
add("point-catch-all", "A class without its own row uses the row with any class.", ["6.10.3"], [SYN],
    usage({"train_mass_kg": 15000, "train_axles": 3, "euro_class": "6", "co2_class": 1}, [ev("gate", M)]), "6.00")
add("point-season-cap", "Two passages in July at the high-season rate (25 each) are capped at 30 a day.", ["6.7", "6.11"], [SYN],
    usage(V40, [ev("bridge", "2026-07-15T10:00:00+02:00"), ev("bridge", "2026-07-15T14:00:00+02:00")]), "30.00")
add("point-undefined-time-class", "A row that would outrank the default row needs a time class the source does not define: the use is unpriced, never guessed.",
    ["6.7", "6.10.3", "8.9"], [SYN], usage(V40, [ev("toll3", M)]), None, complete=False, issues=["unknown_time_class"])
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
    usage({"train_mass_kg": 40000}, [ev("gate", M)]), None, complete=False, issues=["missing_parameter"])
add("outside-validity", "An event after the dataset's validity is not priced.", ["8.2"], [SYN],
    usage(V40, [ev("gate", "2028-01-05T10:00:00+01:00")]), None, complete=False, issues=["outside_validity"])

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
add("od-discount-any-of", "The 10% discount names alternatives (CO2 class 4, or Euro 7): a Euro 7 vehicle of CO2 class 1 gets it. 10.00 less 10%: 9.00.",
    ["6.6.2", "6.11"], [SYN], usage({**V40, "euro_class": "7"}, OD("st-a", "st-b")), "9.00")
add("od-discount-any-of-unknown", "Euro VI without a CO2 class: one alternative fails and the other can't be decided, so the discount is unknown and the statement incomplete.",
    ["6.6.2", "8.9"], [SYN], usage({k: v for k, v in V40.items() if k != "co2_class"}, OD("st-a", "st-b")), "10.00", complete=False, issues=["missing_parameter"])
add("point-passage-group-free-first", "A free passage (Sunday) starts no run: the paid passage 40 minutes later, on Monday, pays 8.40.",
    ["6.11"], [SYN], usage(V40, [ev("gate", "2026-11-15T23:30:00+01:00"), ev("gate", "2026-11-16T00:10:00+01:00")]), "8.40")
add("section-cap-time-class", "A day cap of 20 for night uses only: the two night uses (24) are capped at 20, the day use (12) is not. Section uses 32, plus 3 x 1.25 per km: 35.75.",
    ["6.11"], [SYN], usage(V40, [ev("sec1", "2026-11-17T10:00:00+01:00"), ev("sec1", "2026-11-17T22:30:00+01:00"),
                                ev("sec1", "2026-11-17T23:30:00+01:00")]), "35.75",
    lines=[("sec", "12"), ("sec", "12"), ("sec", "12"), ("seckm", "1.25"), ("seckm", "1.25"), ("seckm", "1.25"), ("sec", "-4")])
add("od-barrier", "A barrier priced from itself to itself: one passage is a trip of one station (2).", ["8.4"], [SYN],
    usage(V40, [ev("c5", "2026-11-16T09:40:00+01:00")]), "2.00", lines=[("odc2", "2.00")])
add("period-tie", "Two consecutive days: one 2-day product and two day products both cost 24; the fewest products win.", ["8.4"], [SYN],
    usage(V40, [ev("vnet", f"2026-11-{d}T10:00:00+01:00") for d in (16, 17)]), "24.00", lines=[("vig", "24")])
add("distance-missing-km", "A network event without km: unpriced, never taken as zero.", ["8.4", "8.9"], [SYN],
    usage(V40, [ev("mw", M)]), None, complete=False, issues=["missing_km"])
add("unknown-object", "An event on an object the dataset does not have makes the statement incomplete.", ["8.9"], [SYN],
    usage(V40, [ev("nowhere", M), ev("gate", M)]), "8.40", complete=False, issues=["unknown_object"])
add("calendar-past-covers-to", "On a weekday after the holiday calendar's covers_to, whether the zone charges can't be decided: unpriced.",
    ["6.7", "8.9"], [SYN], usage(V40, [ev("city", "2027-09-15T10:00:00+02:00")]), None, complete=False, issues=["unknown_time_class"])
add("exemption-user-class", "A user class held by contract (emergency services) exempts the distance charge.", ["6.8", "6.11"], [SYN],
    usage(V40, [ev("mw", M, km=100)], user_classes={SID: ["emergency"]}), None)
add("point-volume", "Price by volume: with 2 crossings earlier this year, the next two are the 3rd (10.00) and the 4th (5.00 from the 4th on).",
    ["6.10.3", "9.1"], [SYN], usage(V40, [ev("tunnel", M), ev("tunnel", "2026-11-16T12:00:00+01:00")], prior_uses={SID: {"tunnel-fee": 2}}),
    "15.00", lines=[("tunnel-fee", "10.00"), ("tunnel-fee", "5.00")])
add("point-volume-unknown", "Price by volume without the earlier crossings: unpriced, never guessed.", ["6.10.3", "8.9"], [SYN],
    usage(V40, [ev("tunnel", M)]), None, complete=False, issues=["missing_count"])
add("rounding-per-use", "Rounded per use before the rules: 2.345 is 2.35, less 10 % is 2.115, total 2.12 (rounded after the rules it would be 2.11).",
    ["8.7"], [SYN], usage(V40, [ev("pier", M)]), "2.12", lines=[("pier-fee", "2.115")])
add("dynamic-tariff", "A charge whose amounts are set in real time is not priced from its indicative rows.", ["6.10.1", "8.9"], [SYN],
    usage(V40, [ev("express", M)]), None, complete=False, issues=["dynamic_tariff"])
UNI = {**V40, "mass_kg": 18000, "axles": 2}
add("per-vehicle-unit", "The motor vehicle pays by its own mass (18 t: 0.12) and the trailer by its own (24 t: 0.09): 12 + 9 for 100 km.",
    ["6.6.1", "8.4"], [SYN], usage({**UNI, "trailer_mass_kg": 24000}, [ev("uni", M, km=100)]), "21.00",
    lines=[("motor-km", "12"), ("trailer-km", "9")])
add("derived-no-trailer", "Without a trailer, trailer_mass_kg is derived as 0 (6.6.1): the trailer charge matches no row and is free; train_mass_kg is derived from mass_kg for the liable-vehicle test.",
    ["6.6.1", "6.10.1"], [SYN], usage({"mass_kg": 18000, "axles": 2, "trailer": False, "euro_class": "6", "co2_class": 1}, [ev("uni", M, km=100)]),
    "12.00", lines=[("motor-km", "12")])
add("derived-trailer-mass-missing", "train_axles 5 and axles 2 derive a trailer of 3 axles, but its mass is not given: the trailer charge is unpriced, never guessed.",
    ["6.6.1", "6.6.2", "8.9"], [SYN], usage(UNI, [ev("uni", M, km=100)]), "12.00", complete=False,
    lines=[("motor-km", "12")], issues=["missing_parameter"])
add("od-per-tonne", "A ferry fare per tonne of load capacity (unit t, mass_basis load_capacity_kg): a semi-trailer of 30 t pays 30 × 9.80; the flat fare up to 5 t doesn't apply (unmatched: free).",
    ["6.6.1", "6.10.2", "8.4"], [SYN], usage({**V40, "load_capacity_kg": 30000}, [ev("quay-a", M, role="entry"), ev("quay-b", "2026-11-16T11:00:00+01:00", role="exit")]),
    "294.00", lines=[("ferry-t", "294.00")])
add("od-per-tonne-light", "Up to 5 t of load capacity the flat fare applies.", ["6.10.2", "8.4"], [SYN],
    usage({**V7, "load_capacity_kg": 4500}, [ev("quay-a", M, role="entry"), ev("quay-b", "2026-11-16T11:00:00+01:00", role="exit")]),
    "45.70", lines=[("ferry", "45.70")])
add("od-per-tonne-missing", "Without load_capacity_kg the fare can't be priced (missing_parameter), never guessed.", ["6.10.2", "8.4", "8.9"], [SYN],
    usage(V40, [ev("quay-a", M, role="entry"), ev("quay-b", "2026-11-16T11:00:00+01:00", role="exit")]), None, complete=False,
    lines=[], issues=["missing_parameter"])
add("od-per-started-tonne", "A ferry fare per started 1,000 kg of the load (unit t, mass_basis load_kg, mass_step_kg 1000): 20,500 kg counts 21 t × 1.26.",
    ["6.6.1", "6.10.2", "8.4"], [SYN], usage({**V40, "load_kg": 20500}, [ev("bank-a", M, role="entry"), ev("bank-b", "2026-11-16T10:30:00+01:00", role="exit")]),
    "26.46", lines=[("river-load", "26.46")])
add("od-per-started-tonne-missing", "Without load_kg the fare per tonne of the load can't be priced (missing_parameter), never guessed.", ["6.10.2", "8.4", "8.9"], [SYN],
    usage(V40, [ev("bank-a", M, role="entry"), ev("bank-b", "2026-11-16T10:30:00+01:00", role="exit")]), None, complete=False,
    lines=[], issues=["missing_parameter"])
NC = "tests/fixtures/no-charge.orct.json"
add("no-charge", "A dataset stating that the area levies no charge (no_charge) prices nothing: an empty, complete statement.", ["6.13", "8.2"], [NC],
    usage(V40), None, lines=[])
AT = "data/carbon-cost/at/at-2026-01-01.orct.json"; ATID = "carbon-cost/at/2026-01-01"
src = "Sum of the 2026 parts of BGBl. II Nr. 298/2025 §§ 2, 8, 9, equal to the per-km totals the WKO publishes, as carbon-cost's TestAustriaTotals asserts them; 100 km."
for name, ta, ax, euro, cls, want in (("e-2-axles", 2, 2, "6", 5, "5.87"), ("a-co2-1-3-axles", 3, 3, "6", 1, "38.56"),
                                      ("a-co2-1-4-axles", 5, 2, "6", 1, "57.24"), ("b-4-axles", 5, 2, "5", 1, "60.24")):
    add(f"at-{name}", f"Austrian HGV toll 2026, {name}: {want}. " + src, ["8.4"], [AT],
        usage({"train_mass_kg": 40000, "train_axles": ta, "axles": ax, "euro_class": euro, "co2_class": cls},
              [{"dataset": ATID, "object": "roads", "time": "2026-06-01T10:00:00+02:00", "km": 100}]), want)
DK = "data/carbon-cost/dk/dk-2026-01-01.orct.json"; DKID = "carbon-cost/dk/2026-01-01"
src = "Vejafgiftsloven rates for 2026 (Skatteministeriet's rate table), as carbon-cost's TestDenmarkTotals asserts them; 100 km."
for name, kg, cls, want in (("15t-co2-1", 15000, 1, "86.00"), ("26t-co2-1", 26000, 1, "100.00"), ("40t-co2-1", 40000, 1, "110.00"),
                            ("40t-co2-5", 40000, 5, "13.00")):
    add(f"dk-{name}", f"Danish HGV toll 2026, {name}: {want} DKK. " + src, ["8.4"], [DK],
        usage({"train_mass_kg": kg, "mass_kg": kg, "train_axles": 5, "axles": 2, "euro_class": "6", "co2_class": cls},
              [{"dataset": DKID, "object": "roads", "time": "2026-06-01T10:00:00+02:00", "km": 100}]), want, currency="DKK")
add("period-rolling-clocks-back", "A rolling P1D bought at 10:00 the day before the clocks go back lasts 24 hours, to 09:00: a use at 09:30 needs a second one (20).",
    ["8.4"], [SYN], usage(V40, [ev("rnet", "2026-10-24T10:00:00+02:00"), ev("rnet", "2026-10-25T09:30:00+01:00")]), "20.00", lines=[("rvig", "10"), ("rvig", "10")])
for old in glob.glob("tests/vectors/*.json"):
    os.remove(old)
for i, (name, v) in enumerate(V, 1):
    with open(f"tests/vectors/{i:03d}-{name}.json", "w") as fh:
        json.dump(v, fh, indent=1, ensure_ascii=False); fh.write("\n")
print(len(V), "vectors")
