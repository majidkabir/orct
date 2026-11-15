#!/usr/bin/env python3
"""Convert carbon-cost's rate tables (rates/data/*.json) to ORCT 0.1.

Usage: convert_carbon_cost.py <carbon-cost checkout> <out dir> [--commit SHA]

Writes <out dir>/<country>/<file stem>.orct.json and <out dir>/index.json.
Every table is converted; what ORCT 0.1 can't express yet is kept under
extensions["x-carbon-cost"] and listed in coverage as partial, so nothing
is lost and a calculator knows what it would miss.
"""
import json
import os
import re
import sys

REPO = "https://github.com/majidkabir/carbon-cost"
PUBLISHER = "carbon-cost (majidkabir/carbon-cost), compiled from the sources listed"
# Table keys that carry no pricing rule: kept as extensions without
# making the dataset partial.
INFO_KEYS = {"osm_extract", "crossings"}

COMPONENTS = {
    "toll": "toll", "infrastructure": "infrastructure", "congestion": "congestion",
    "air": "air", "noise": "noise", "air_noise": "air_noise", "co2": "co2",
}


def component(c):
    return COMPONENTS.get(c, "x-" + re.sub(r"[^a-z0-9_-]", "_", c.lower()))


def rng(lo, hi):
    r = {}
    if lo:
        r["min"] = lo
    if hi:
        r["max"] = hi
    return r or None


def lonlat(p):
    return [p["lon"], p["lat"]]


def place(p):
    out = {"geometry": {"type": "Point", "coordinates": lonlat(p)}}
    if p.get("name"):
        out["name"] = p["name"]
    if p.get("heading") is not None:
        out["heading"] = p["heading"]
    return out


class Classes:
    """The dataset's vehicle classes, one per distinct criteria and label."""

    def __init__(self):
        self.items, self.by_key = [], {}

    def get(self, criteria, label=None, fallback=None):
        criteria = {k: v for k, v in criteria.items() if v not in (None, [], {})}
        key = json.dumps([criteria, label], sort_keys=True)
        if key in self.by_key:
            return self.by_key[key]
        if not criteria and label is None:
            cid = "any"
        else:
            ids = {c["id"] for c in self.items}
            if label is None:
                n = 1
                while f"c{n}" in ids:
                    n += 1
                cid = f"c{n}"
            else:
                base = "c-" + re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-")
                cid, n = base, 1
                while cid in ids:
                    n += 1
                    cid = f"{base}-{n}"
        c = {"id": cid, "criteria": criteria}
        if label is not None:
            c["label"] = label
        if fallback:
            c["fallback"] = fallback
        self.items.append(c)
        self.by_key[key] = cid
        return cid

    def ordered(self):
        # "any" last: the first class a vehicle meets wins.
        return [c for c in self.items if c["id"] != "any"] + [c for c in self.items if c["id"] == "any"]


def variants(default, **named):
    v = {k: x for k, x in named.items() if x}
    if not v:
        return default
    return {"default": default, **v}


class Builder:
    def __init__(self, table, path, commit):
        self.t = table
        self.classes = Classes()
        self.network, self.charges, self.modifiers = [], [], []
        self.ext, self.partial = {}, []
        self.net_ids = set()
        stem = os.path.basename(path)[:-5]
        self.dataset = {
            "id": stem,
            "scheme": re.sub(r"-\d{4}-\d{2}-\d{2}$", "", stem),
            "country": table["country"],
            "currency": table["currency"],
            "valid_from": table["valid_from"],
            "name": table["name"],
            "method": table.get("law", ""),
            "publisher": PUBLISHER,
            "derived_from": {"repository": REPO, "path": "rates/data/" + os.path.basename(path)},
        }
        # The carbon-cost commit is in index.json only, so a new commit there
        # doesn't rewrite every file.
        if table.get("region"):
            self.dataset["region"] = table["region"]
        if table.get("valid_to"):
            self.dataset["valid_to"] = table["valid_to"]
        self.sources = [{"id": f"s{i + 1}", "title": s["title"], "url": s["url"]} for i, s in enumerate(table.get("sources", []))]
        self.src = [s["id"] for s in self.sources]
        if not self.sources:
            self.partial.append(("dataset", "the table lists no source"))

    def net(self, el):
        if el["id"] not in self.net_ids:
            self.net_ids.add(el["id"])
            self.network.append(el)
        return el["id"]

    def keep(self, key, value, reason=None):
        self.ext[key] = value
        if reason:
            self.partial.append(("dataset", reason))

    def doc(self, vehicles):
        coverage = [{"scope": s, "status": "partial", "reason": r} for s, r in self.partial]
        if "ESTIMATE" in self.t.get("name", "") or self.t.get("law", "").startswith("Estimate"):
            coverage.append({"scope": "dataset", "status": "partial", "reason": "the source table is an estimate; see dataset.method"})
        if not coverage:
            coverage = [{"scope": "dataset", "status": "complete"}]
        out = {
            "orct_version": "0.1",
            "dataset": self.dataset,
            "sources": self.sources or [{"id": "s0", "title": "carbon-cost table", "url": REPO}],
            "vehicles": vehicles,
            "classes": self.classes.ordered() or [{"id": "any", "criteria": {}}],
            "network": self.network,
            "charges": self.charges,
            "tax": {"included": None, "note": "Not recorded as a field in the source table; dataset.method says where the sources state it."},
            "coverage": coverage,
        }
        if not self.sources:
            for c in out["charges"]:
                c["sources"] = ["s0"]
        if self.modifiers:
            out["modifiers"] = self.modifiers
        if self.ext:
            out["extensions"] = {"x-carbon-cost": self.ext}
        return out


def convert_table(t, path, commit):
    b = Builder(t, path, commit)
    used = {"country", "region", "currency", "valid_from", "valid_to", "name", "law", "sources",
            "vehicles", "min_kg", "tolled_roads", "motor_axles", "rows", "per_tonne_km",
            "max_chargeable_kg", "per_day", "day", "exemptions", "motorway_share", "suburban_share",
            "surcharges", "closed_systems", "toll_points", "point_match_km", "sections", "congestion"}
    vehicles = {"description": t.get("vehicles", ""), "min_mass_kg": t.get("min_kg", 0),
                "axle_basis": "motor_vehicle" if t.get("motor_axles") else "combination"}
    roads = {"id": "roads", "kind": "road_class", "description": t.get("tolled_roads", "")}

    # Rows: per km, per tonne-km or per day.
    groups = {}
    for r in t.get("rows", []):
        groups.setdefault((r["component"], r.get("road", ""), r.get("area", ""), r.get("operator", "")), []).append(r)
    row_charges = {}
    for (comp, road, area, op), rows in groups.items():
        if op:
            parts = op.split("|")
            el = {"id": "op:" + op, "kind": "operator", "operator": parts[0]}
            if len(parts) > 1:
                el["ref"] = parts[1]
            if len(parts) > 2:
                el["label"] = parts[2]
            if road:
                el["road_type"] = road
        elif road or area:
            el = {"id": "road:" + ":".join(x for x in (road, area) if x), "kind": "road_class"}
            if road:
                el["road_type"] = road
            if area:
                el["area"] = area
        else:
            el = roads
        nid = b.net(el)
        rates = {}
        for r in rows:
            cid = b.classes.get({"mass_kg": rng(r.get("min_kg"), r.get("max_kg")),
                                 "axles": rng(r.get("min_axles"), r.get("max_axles")),
                                 "euro": r.get("euro"), "co2_class": r.get("co2_class")})
            if cid in rates and rates[cid] != r["rate"]:
                b.partial.append((nid, f"two rates for one class in {comp}; the first is kept"))
                continue
            rates[cid] = r["rate"]
        ch = {"id": f"{comp}@{nid}", "type": "distance", "component": component(comp),
              "applies_to": [nid], "sources": b.src, "rates": rates}
        if t.get("per_tonne_km"):
            ch["type"], ch["unit"] = "quantity", "tonne_km"
            if t.get("max_chargeable_kg"):
                ch["max_mass_kg"] = t["max_chargeable_kg"]
        elif t.get("per_day"):
            ch["type"], ch["period"] = "period", "day"
            if t.get("day") in ("calendar", "24h"):
                ch["day_basis"] = t["day"]
            else:
                b.partial.append((ch["id"], "what counts as a day isn't known; one day is charged per trip"))
        b.charges.append(ch)
        row_charges.setdefault(comp, []).append(ch["id"])
    all_rows = [c for ids in row_charges.values() for c in ids]
    if roads["id"] not in b.net_ids:
        b.net(roads)

    for e in t.get("exemptions", []):
        b.modifiers.append({"kind": "exemption", "applies_to": all_rows, "params": e})
    if t.get("motorway_share"):
        b.modifiers.append({"kind": "assumed_share", "applies_to": all_rows,
                            "params": {"of": "motorway", "share": t["motorway_share"]}})
    for rt, share in (t.get("suburban_share") or {}).items():
        p = {"of": "suburban", "share": share}
        if rt:
            p["road_type"] = rt
        b.modifiers.append({"kind": "assumed_share", "applies_to": all_rows, "params": p})

    for s in t.get("surcharges", []):
        sid = b.net({"id": "stretch:" + s["id"], "kind": "stretch", "name": s["name"],
                     "geometry": {"type": "LineString", "coordinates": [lonlat(p) for p in s["points"]]},
                     "point_names": [p["name"] for p in s["points"]]})
        b.modifiers.append({"kind": "factor", "applies_to": row_charges.get(s["component"], []),
                            "params": {"stretch": sid, "factor": s["factor"], "note": s.get("law", "")}})

    system_charge = {}
    for i, s in enumerate(t.get("closed_systems", [])):
        convert_system(b, i, s, system_charge)
    convert_points(b, t, system_charge)
    if t.get("sections"):
        convert_sections(b, t["sections"])

    for k in sorted(INFO_KEYS & t.keys()):
        b.keep(k, t[k])
    for k in sorted(set(t) - used - INFO_KEYS):
        b.keep(k, t[k], f"{k} is kept as an extension (no ORCT 0.1 field yet)")
    return b.doc(vehicles)


def convert_system(b, i, s, system_charge):
    cid = f"system:{i + 1}"
    system_charge[s["name"]] = cid
    stations = {}
    for st in s["stations"]:
        el = {"id": f"st:{i + 1}:{st['name']}", "kind": "station", "name": st["name"],
              "geometry": {"type": "MultiPoint", "coordinates": [lonlat(p) for p in st["points"]]},
              "point_names": [p.get("name", "") for p in st["points"]]}
        if any(p.get("heading") is not None for p in st["points"]):
            el["headings"] = [p.get("heading") for p in st["points"]]
        if s.get("station_match_km"):
            el["match_km"] = s["station_match_km"]
        stations[st["name"]] = b.net(el)
    gid = {}
    for g in s["groups"]:
        crit = {"mass_kg": rng(g.get("min_kg"), None), "axles": rng(g.get("min_axles"), g.get("max_axles")),
                "euro": g.get("euro")}
        if g.get("min_length_m") or g.get("max_length_m"):
            crit["length_m"] = {k: v for k, v in (("over", g.get("min_length_m")), ("max", g.get("max_length_m"))) if v}
        gid[g["name"]] = b.classes.get(crit, label=g["name"])
    for g in s["groups"]:
        if g.get("base"):
            for c in b.classes.items:
                if c["id"] == gid[g["name"]]:
                    c["fallback"] = gid[g["base"]]
    pairs, odd, unplaced = [], {}, set()
    etc, night = s.get("etc_prices") or {}, s.get("night_prices") or {}
    for key in sorted(set(s["prices"]) | set(etc) | set(night)):
        entry, exit_ = key.split("|")
        for name in (entry, exit_):
            if name not in stations:
                # Priced in the tariff but not placed on the map: listed
                # without geometry, so the pair is kept but can't match a route.
                stations[name] = b.net({"id": f"st:{i + 1}:{name}", "kind": "station", "name": name})
                unplaced.add(name)
        rates = {}
        for g in sorted(set(s["prices"].get(key, {})) | set(etc.get(key, {})) | set(night.get(key, {}))):
            d = s["prices"].get(key, {}).get(g)
            e, n = etc.get(key, {}).get(g), night.get(key, {}).get(g)
            if g not in gid or d is None:
                odd.setdefault(key, {})[g] = {"default": d, "electronic": e, "night": n}
                continue
            rates[gid[g]] = variants(d, electronic=e, night=n)
        if rates:
            pairs.append({"entry": stations[entry], "exit": stations[exit_], "rates": rates})
    ch = {"id": cid, "name": s["name"], "type": "od_matrix", "component": "toll",
          "applies_to": sorted(set(stations.values())), "sources": b.src, "rates": {}, "pairs": pairs,
          "pairing": "chain" if s.get("chain") else "single_ticket"}
    if s.get("law"):
        ch["method"] = s["law"]
    if s.get("directed"):
        ch["directed"] = True
    b.charges.append(ch)
    if etc:
        b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "electronic", "payment": "electronic"}})
    if s.get("night_hours"):
        b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "night", "hours": s["night_hours"]}})
    if s.get("free_hours"):
        b.modifiers.append({"kind": "free_hours", "applies_to": [cid], "params": {"hours": s["free_hours"]}})
    for d in s.get("discounts", []):
        p = {"name": d["name"], "percent": d["percent"]}
        if d.get("etc"):
            p["payment"] = "electronic"
        for k in ("euro", "co2_class"):
            if d.get(k):
                p[k] = d[k]
        b.modifiers.append({"kind": "discount", "applies_to": [cid], "params": p})
    if unplaced:
        b.partial.append((cid, f"{len(unplaced)} stations in the tariff aren't placed on the map; their pairs can't be matched to a route"))
    if odd:
        b.ext.setdefault("closed_system_prices_not_mapped", {})[s["name"]] = odd
        b.partial.append((cid, "some prices name a vehicle group the system doesn't list, or have only an electronic or night price; kept as an extension"))


def convert_points(b, t, system_charge):
    cong = t.get("congestion")
    groups, peak = {}, 0
    for j, p in enumerate(t.get("toll_points", [])):
        el = {"id": f"pt:{j + 1}", "kind": "point", "name": p["name"],
              "geometry": {"type": "Point", "coordinates": lonlat(p)}}
        if p.get("heading") is not None:
            el["heading"] = p["heading"]
        if t.get("point_match_km"):
            el["match_km"] = t["point_match_km"]
        nid = b.net(el)
        cid = f"point:{j + 1}"
        rates = {}
        if p.get("classes"):
            for c in p["classes"]:
                crit = {"mass_kg": rng(c.get("min_kg"), c.get("max_kg")), "axles": rng(c.get("min_axles"), c.get("max_axles"))}
                if c.get("min_length_m") or c.get("max_length_m"):
                    crit["length_m"] = {k: v for k, v in (("over", c.get("min_length_m")), ("max", c.get("max_length_m"))) if v}
                rates[b.classes.get(crit)] = variants(c["rate"], electronic=c.get("etc_rate"), high_season=c.get("high_rate"),
                                                     high_season_electronic=c.get("high_etc_rate"), night=c.get("night_rate"),
                                                     night_electronic=c.get("night_etc_rate"))
        else:
            rates[b.classes.get({})] = variants(p["rate"], peak=p.get("peak_rate"))
        ch = {"id": cid, "name": p["name"], "type": "point",
              "component": "congestion" if p.get("schedule") else "toll",
              "applies_to": [nid], "sources": b.src, "rates": rates}
        if p.get("project"):
            ch["method"] = "Toll project: " + p["project"]
        for k in ("valid_from", "valid_to"):
            if p.get(k):
                ch[k] = p[k]
        b.charges.append(ch)
        if p.get("peak_rate"):
            peak += 1
        if any(c.get("etc_rate") or c.get("high_etc_rate") or c.get("night_etc_rate") for c in p.get("classes", [])):
            b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "electronic", "payment": "electronic"}})
        if p.get("high_season"):
            b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "high_season", "season": p["high_season"]}})
        if p.get("night_hours"):
            b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "night", "hours": p["night_hours"]}})
        if p.get("free_hours"):
            b.modifiers.append({"kind": "free_hours", "applies_to": [cid], "params": {"hours": p["free_hours"]}})
        if p.get("group"):
            groups.setdefault((p["group"], p.get("group_minutes", 0)), []).append(cid)
        if p.get("within"):
            if p["within"] in system_charge:
                b.modifiers.append({"kind": "included_in", "applies_to": [cid], "params": {"charge": system_charge[p["within"]]}})
            else:
                b.partial.append((cid, f"included in a system ({p['within']}) the table doesn't list"))
        if p.get("schedule"):
            if cong and p["schedule"] in cong.get("schedules", {}):
                b.modifiers.append({"kind": "time_schedule", "applies_to": [cid],
                                    "params": {"schedule": cong["schedules"][p["schedule"]], "name": p["schedule"]}})
            else:
                b.partial.append((cid, f"schedule {p['schedule']} isn't in the table"))
    if peak:
        b.partial.append(("dataset", f"{peak} toll points charge a peak rate whose rush hours aren't in the source table"))
    for (g, minutes), ids in sorted(groups.items()):
        b.modifiers.append({"kind": "passage_group", "applies_to": ids, "params": {"group": g, "minutes": minutes}})
    if cong:
        cids = [c["id"] for c in b.charges if c["type"] == "point" and c["component"] == "congestion"]
        if cong.get("day_cap"):
            b.modifiers.append({"kind": "cap", "applies_to": cids, "params": {"per": "day", "amount": cong["day_cap"],
                                                                             **({"high_season": cong["day_cap_high"]} if cong.get("day_cap_high") else {})}})
        if cong.get("multi_pass_minutes"):
            b.modifiers.append({"kind": "multi_pass", "applies_to": cids, "params": {"minutes": cong["multi_pass_minutes"], "pays": "highest"}})
        rest = {k: v for k, v in cong.items() if k not in ("schedules", "day_cap", "day_cap_high", "multi_pass_minutes")}
        if rest:
            b.keep("congestion", rest, "the congestion tax's taxed days (high season, July, holiday eves) are kept as an extension")


def convert_sections(b, secs):
    axle_cols = [{"max": 2}, {"min": 3, "max": 3}, {"min": 4}]
    groups = {"E": [5], "A": [1, 2, 3, 4]}
    rest = {k: v for k, v in secs.items() if k not in ("list", "law", "tariff_groups")}
    slovenia = []
    for s in secs["list"]:
        el = {"id": "sec:" + s["id"], "kind": "section", "name": s["name"], "road": s["road"],
              "from": place(s["from"]), "to": place(s["to"])}
        if s.get("km"):
            el["km"] = s["km"]
        if s.get("area"):
            el["area"] = s["area"]
        nid = b.net(el)
        if s.get("classes") or s.get("tier"):
            slovenia.append({k: s[k] for k in ("id", "classes", "tier", "area") if k in s})
        if not s.get("tariff"):
            continue
        rates = {}
        for g, cols in s["tariff"].items():
            for k, v in enumerate(cols):
                cid = b.classes.get({"axles": axle_cols[k], "co2_class": groups.get(g)}, label=f"{g}/{['2', '3', '4+'][k]} axles")
                night = s.get("night_kat4", {}).get(g) if k == 2 else None
                rates[cid] = variants(v, night=night)
        cid = "section:" + s["id"]
        ch = {"id": cid, "name": s["name"], "type": "point", "component": "infrastructure",
              "applies_to": [nid], "sources": b.src, "rates": rates}
        if secs.get("law"):
            ch["method"] = secs["law"] + (" " + secs["tariff_groups"] if secs.get("tariff_groups") else "")
        b.charges.append(ch)
        if s.get("night_kat4"):
            b.modifiers.append({"kind": "variant", "applies_to": [cid], "params": {"name": "night", "hours": ["22:00", "05:00"]}})
    if slovenia:
        b.keep("section_classes", slovenia, "per-section charges by toll class and emission column are kept as an extension")
    if rest:
        b.keep("sections", rest, "per-km charges on sections are kept as an extension")


def convert_zone(z, path, commit):
    b = Builder(z, path, commit)
    used = {"country", "currency", "valid_from", "valid_to", "name", "law", "sources", "min_kg", "charge",
            "exempt_euro", "euro_charges", "weekdays", "weekends", "no_charge", "polygons", "holes", "osm_extract"}
    nid = b.net({"id": "zone", "kind": "zone", "name": z["name"],
                 "geometry": {"type": "MultiPolygon", "coordinates": [[ring] for ring in z["polygons"]]}})
    ch = {"id": "zone-charge", "name": z["name"], "type": "zone", "component": "access",
          "applies_to": [nid], "sources": b.src, "rates": {}}
    if z.get("holes"):
        ch["excludes"] = [b.net({"id": "zone-holes", "kind": "zone", "name": "areas cut out of the zone",
                                 "geometry": {"type": "MultiPolygon", "coordinates": [[ring] for ring in z["holes"]]}})]
    top = z.get("exempt_euro") or 7
    if z.get("exempt_euro"):
        ch["rates"][b.classes.get({"euro": list(range(z["exempt_euro"], 7))})] = 0
    for e in sorted(z.get("euro_charges", []), key=lambda e: -e["min_euro"]):
        ch["rates"][b.classes.get({"euro": list(range(e["min_euro"], top))})] = e["charge"]
        top = e["min_euro"]
    ch["rates"][b.classes.get({})] = z["charge"]
    b.charges.append(ch)
    hours = {k: z[k] for k in ("weekdays", "weekends", "no_charge") if z.get(k)}
    if hours:
        b.modifiers.append({"kind": "charging_hours", "applies_to": ["zone-charge"], "params": hours})
    if z.get("osm_extract"):
        b.keep("osm_extract", z["osm_extract"])
    for k in sorted(set(z) - used):
        b.keep(k, z[k], f"{k} is kept as an extension (no ORCT 0.1 field yet)")
    return b.doc({"description": "vehicles of at least min_mass_kg", "min_mass_kg": z.get("min_kg", 0)})


def convert_fuel(f, path, commit):
    b = Builder(f, path, commit)
    used = {"country", "currency", "valid_from", "valid_to", "name", "law", "sources", "rate_per_t"}
    b.charges.append({"id": "fuel-co2", "name": f["name"], "type": "quantity", "component": "carbon_price",
                      "unit": "t_co2", "applies_to": [], "sources": b.src, "rates": {b.classes.get({}): f["rate_per_t"]}})
    for k in sorted(set(f) - used):
        b.keep(k, f[k], f"{k} is kept as an extension (no ORCT 0.1 field yet)")
    return b.doc({"description": "CO2 from fuel bought in the country, per tonne", "min_mass_kg": 0})


def main():
    args = sys.argv[1:]
    commit = None
    if "--commit" in args:
        i = args.index("--commit")
        commit = args[i + 1]
        del args[i:i + 2]
    src, out = args
    data = os.path.join(src, "rates", "data")
    index = []
    for name in sorted(os.listdir(data)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(data, name)
        with open(path) as fh:
            t = json.load(fh)
        if name.startswith("zone-"):
            doc = convert_zone(t, path, commit)
        elif name.startswith("fuelco2-"):
            doc = convert_fuel(t, path, commit)
        else:
            doc = convert_table(t, path, commit)
        cc = doc["dataset"]["country"].lower()
        rel = f"{cc}/{name[:-5]}.orct.json"
        os.makedirs(os.path.join(out, cc), exist_ok=True)
        with open(os.path.join(out, rel), "w") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        ds = doc["dataset"]
        index.append({"id": ds["id"], "country": ds["country"], "file": rel, "name": ds["name"],
                      "valid_from": ds["valid_from"], "valid_to": ds.get("valid_to"),
                      "coverage": "complete" if doc["coverage"][0]["status"] == "complete" else "partial"})
    with open(os.path.join(out, "index.json"), "w") as fh:
        json.dump({"orct_version": "0.1", "derived_from": {"repository": REPO, "commit": commit}, "datasets": index},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"{len(index)} datasets")


if __name__ == "__main__":
    main()
