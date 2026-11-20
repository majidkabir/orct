"""Writes schema/*.schema.json (Annex A). Run from the repository root."""
import json
DEC = {"type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$"}
DATE = {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
ID = {"type": "string", "minLength": 1, "pattern": "^\\S(.*\\S)?$"}
def obj(props, req=(), extra=False):
    o = {"type": "object", "properties": props, "additionalProperties": extra}
    if req: o["required"] = list(req)
    return o
num_cond = obj({"min": {"type": "number"}, "max": {"type": "number"}, "gt": {"type": "number"}, "lt": {"type": "number"}})
str_list = lambda enum=None: {"type": "array", "minItems": 1, "items": ({"enum": enum} if enum else {"type": "string"})}
EURO = ["0", "1", "2", "3", "4", "5", "EEV", "6", "7"]
ENERGY = ["diesel", "petrol", "lpg", "cng", "lng", "electric", "hydrogen", "hybrid", "other"]
CATEGORY = ["M1", "M2", "M3", "N1", "N2", "N3", "L"]
criteria = obj({
    "mass_kg": num_cond, "train_mass_kg": num_cond, "axles": num_cond, "train_axles": num_cond,
    "trailer_mass_kg": num_cond, "trailer_axles": num_cond, "load_capacity_kg": num_cond,
    "length_m": num_cond, "train_length_m": num_cond, "height_m": num_cond, "first_axle_height_m": num_cond,
    "width_m": num_cond, "euro_class": str_list(EURO),
    "co2_class": {"type": "array", "minItems": 1, "items": {"type": "integer", "minimum": 1, "maximum": 5}},
    "energy": str_list(ENERGY), "category": str_list(CATEGORY), "trailer": {"type": "boolean"},
    "any_of": {"type": "array", "minItems": 2, "items": {"$ref": "#/$defs/criteria"}}})
geometry = obj({"type": {"enum": ["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]},
                "coordinates": {"type": "array"}}, ["type", "coordinates"])
place = obj({"name": {"type": "string"}, "geometry": {"$ref": "#/$defs/geometry"}, "heading": {"type": "number"}}, ["geometry"])
mmdd_or_date = {"type": "string", "pattern": "^(\\d{4}-)?\\d{2}-\\d{2}$"}
day_core = {
    "weekdays": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 7}},
    "months": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 12}},
    "dates": {"type": "array", "items": mmdd_or_date},
    "date_ranges": {"type": "array", "items": {"type": "array", "items": mmdd_or_date, "minItems": 2, "maxItems": 2}},
    "easter": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}},
    "calendars": {"type": "array", "items": ID}}
days = {"type": "array", "minItems": 1, "items": obj({**day_core, "exclude": obj(day_core)})}
hhmm = {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$|^24:00$"}
tax = obj({"basis": {"enum": ["included", "excluded", "not_applicable", "unknown"]}, "rate": DEC,
           "name": {"type": "string"}, "note": {"type": "string"}}, ["basis"])
names = {"type": "object", "additionalProperties": {"type": "string"}}
COLUMNS = ["object", "entry", "exit", "vehicle_class", "time_class", "user_class", "product", "volume", "priority", "amount"]
COMPONENTS = ["infrastructure", "air_pollution", "noise", "air_pollution_noise", "co2", "congestion", "markup",
              "access", "carbon_price", "unspecified", "other"]
FEATURES = ["type.distance", "type.section", "type.od", "type.point", "type.area", "type.period", "type.quantity",
            "time_classes", "calendars", "user_classes", "rounding", "volume", "dynamic", "rule.exemption",
            "rule.included_in", "rule.passage_group", "rule.factor", "rule.discount", "rule.minimum", "rule.cap"]
charge = obj({
    "id": ID, "name": {"type": "string"},
    "type": {"enum": ["distance", "section", "od", "point", "area", "period", "quantity"]},
    "component": {"enum": COMPONENTS}, "component_label": {"type": "string"},
    "unit": {"enum": ["km", "tkm", "use", "trip", "passage", "t", "day", "entry", "product", "t_co2", "litre", "kg", "kwh"]},
    "columns": {"type": "array", "items": {"enum": COLUMNS}, "uniqueItems": True, "contains": {"const": "amount"}},
    "rows": {"type": "array", "items": {"type": "array", "items": {"type": ["string", "integer", "null"]}}},
    "objects": {"type": "array", "items": ID},
    "sources": {"type": "array", "minItems": 1, "items": ID},
    "basis": {"enum": ["official", "transcribed", "derived", "estimated"]},
    "unmatched": {"enum": ["unpriced", "free"]},
    "time_basis": {"enum": ["entry", "exit", "event"]},
    "rounding": obj({"increment": DEC, "mode": {"enum": ["half_up", "half_even", "up", "down"]},
                     "stage": {"enum": ["use", "line", "charge"]}}, ["increment", "mode", "stage"]),
    "tax": tax, "valid_from": DATE, "valid_to": DATE, "method": {"type": "string"},
    "mass_basis": {"enum": ["mass_kg", "train_mass_kg", "trailer_mass_kg", "load_capacity_kg", "load_kg"]}, "mass_cap_kg": {"type": "integer"},
    "mass_step_kg": {"type": "integer", "minimum": 1},
    "directed": {"type": "boolean"},
    "volume": obj({"per": {"enum": ["day", "month", "year"]}, "counts": {"enum": ["vehicle", "contract"]}}, ["per", "counts"]),
    "dynamic": obj({"url": {"type": "string"}, "note": {"type": "string"}}, ["url"]),
    "day_basis": {"enum": ["calendar", "rolling"]}},
    ["id", "type", "component", "unit", "columns", "rows", "sources", "basis"])
charge["allOf"] = [
    {"if": {"properties": {"columns": {"contains": {"const": "volume"}}}, "required": ["columns"]}, "then": {"required": ["volume"]}},
    {"if": {"properties": {"type": {"const": "distance"}}}, "then": {"properties": {"unit": {"enum": ["km", "tkm"]}}}},
    {"if": {"properties": {"type": {"const": "section"}}}, "then": {"properties": {"unit": {"enum": ["use", "km"]}}}},
    {"if": {"properties": {"type": {"const": "od"}}}, "then": {"properties": {"unit": {"enum": ["trip", "t"]},
        "columns": {"allOf": [{"contains": {"const": "entry"}}, {"contains": {"const": "exit"}}]}}}},
    {"if": {"properties": {"type": {"const": "point"}}}, "then": {"properties": {"unit": {"enum": ["passage", "t"]}}}},
    {"if": {"properties": {"type": {"const": "area"}}}, "then": {"properties": {"unit": {"enum": ["day", "entry"]}}}},
    {"if": {"properties": {"type": {"const": "period"}}}, "then": {"properties": {"unit": {"const": "product"},
        "columns": {"contains": {"const": "product"}}}}},
    {"if": {"properties": {"type": {"const": "quantity"}}}, "then": {"properties": {"unit": {"enum": ["t_co2", "litre", "kg", "kwh"]}}}},
]
NOTE = {"type": "string"}
CRIT = {"$ref": "#/$defs/criteria"}
IDS = {"type": "array", "minItems": 1, "items": ID}
PARAMS = {
    "exemption": {**obj({"criteria": CRIT, "user_class": ID, "from": DATE, "until": DATE, "note": NOTE}),
                  "anyOf": [{"required": ["criteria"]}, {"required": ["user_class"]}]},
    "included_in": obj({"charge": ID, "objects": IDS, "note": NOTE}, ["charge"]),
    "passage_group": obj({"objects": IDS, "minutes": {"type": "integer", "minimum": 1}, "pays": {"enum": ["first", "highest"]},
                          "note": NOTE}, ["objects", "minutes", "pays"]),
    "factor": obj({"object": ID, "factor": DEC, "note": NOTE}, ["object", "factor"]),
    "discount": obj({"name": {"type": "string"}, "percent": DEC, "criteria": CRIT, "user_class": ID,
                     "payment": {"type": "array", "minItems": 1, "items": {"enum": ["electronic", "account", "card", "cash"]}},
                     "note": NOTE}, ["name", "percent"]),
    "minimum": obj({"per": {"enum": ["usage"]}, "amount": DEC, "note": NOTE}, ["per", "amount"]),
    "cap": obj({"per": {"enum": ["day", "month", "usage"]}, "amount": DEC, "time_class": ID, "note": NOTE}, ["per", "amount"])}
rule = {**obj({"id": ID, "kind": {"enum": list(PARAMS)},
               "applies_to": {"type": "array", "minItems": 1, "items": ID}, "params": {"type": "object"}},
              ["id", "kind", "applies_to", "params"]),
        "allOf": [{"if": {"properties": {"kind": {"const": k}}}, "then": {"properties": {"params": v}}} for k, v in PARAMS.items()]}
dataset = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-0.3.schema.json",
    "title": "ORCT 0.3 dataset",
    **obj({
        "orct": {"const": "0.3"},
        "dataset": obj({
            "id": ID, "version": {"type": "string"},
            "scheme": obj({"id": ID, "name": {"type": "string"}, "country": {"type": "string", "pattern": "^[A-Z]{2}$"},
                           "region": {"type": "string", "pattern": "^[A-Z]{2}-[A-Z0-9]{1,3}$"}}, ["id", "name", "country"]),
            "toll_charger": obj({"name": {"type": "string"}, "country": {"type": "string", "pattern": "^[A-Z]{2}$"}, "url": {"type": "string"},
                                 "efc_provider": obj({"country_code": {"type": "string"}, "issuer_id": {"type": "integer"}},
                                                     ["country_code", "issuer_id"])}, ["name"]),
            "publisher": obj({"name": {"type": "string"}, "role": {"enum": ["toll_charger", "authority", "third_party"]},
                              "url": {"type": "string"}}, ["name", "role"]),
            "valid_from": DATE, "valid_to": DATE,
            "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
            "timezone": {"type": "string", "pattern": "^[A-Za-z_]+(/[A-Za-z0-9_+-]+)*$"},
            "license": {"type": "string"}, "method": {"type": "string"}, "names": names,
            "derived_from": obj({"url": {"type": "string"}, "path": {"type": "string"}, "commit": {"type": "string"}}, ["url"]),
            "efc_context": obj({"standard": {"enum": ["ISO 17575-3", "EN 16986", "ISO 12855"]}, "version": {"type": "string"},
                                "valid_from": DATE}, ["standard", "version"]),
            "required_features": {"type": "array", "uniqueItems": True, "items": {"enum": FEATURES}}},
            ["id", "scheme", "publisher", "valid_from", "currency", "timezone", "license", "method", "required_features"]),
        "sources": {"type": "array", "minItems": 1, "items": obj({
            "id": ID, "title": {"type": "string"}, "url": {"type": "string"}, "legal_act": {"type": "string"},
            "retrieved": DATE, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "locator": {"type": "string"}},
            ["id", "title", "url"])},
        "tax": tax,
        "liable_vehicles": obj({"description": {"type": "string"}, "criteria": {"$ref": "#/$defs/criteria"}}, ["criteria"]),
        "vehicle_class_sets": {"type": "array", "items": obj({
            "id": ID, "name": {"type": "string"},
            "classes": {"type": "array", "minItems": 1, "items": obj({
                "id": ID, "label": {"type": "string"}, "criteria": {"$ref": "#/$defs/criteria"}, "fallback": ID},
                ["id", "criteria"])}}, ["id", "classes"])},
        "time_classes": {"type": "array", "items": obj({
            "id": ID, "label": {"type": "string"}, "days": days,
            "times": {"type": "array", "items": {"type": "array", "items": hhmm, "minItems": 2, "maxItems": 2}},
            "defined": {"type": "boolean"}, "note": {"type": "string"}}, ["id"])},
        "calendars": {"type": "array", "items": obj({"id": ID, "name": {"type": "string"},
                                                    "dates": {"type": "array", "items": DATE}, "covers_to": DATE},
                                                   ["id", "dates", "covers_to"])},
        "user_classes": {"type": "array", "items": obj({
            "id": ID, "label": {"type": "string"},
            "payment": {"type": "array", "items": {"enum": ["electronic", "account", "card", "cash"]}},
            "note": {"type": "string"}}, ["id"])},
        "charge_objects": {"type": "array", "items": obj({
            "id": ID, "type": {"enum": ["network", "section", "station", "point", "area", "jurisdiction"]},
            "parents": {"type": "array", "minItems": 1, "uniqueItems": True, "items": ID}, "name": {"type": "string"}, "names": names, "code": {"type": "string"},
            "operator": {"type": "string"}, "road": {"type": "string"},
            "network": obj({"road_types": {"type": "array", "items": {"enum": ["motorway", "trunk", "other"]}},
                            "area": {"enum": ["suburban", "interurban"]}, "description": {"type": "string"}}),
            "from": {"$ref": "#/$defs/place"}, "to": {"$ref": "#/$defs/place"}, "length_km": {"type": "number"},
            "location": obj({"geometry": {"$ref": "#/$defs/geometry"}, "openlr": {"type": "string"},
                             "osm": {"type": "array", "items": {"type": "string"}},
                             "heading": {"type": "number"}, "match_m": {"type": "number"},
                             "headings": {"type": "array", "items": {"type": ["number", "null"]}},
                             "point_names": {"type": "array", "items": {"type": "string"}}}),
            "jurisdiction": obj({"country": {"type": "string", "pattern": "^[A-Z]{2}$"},
                                 "region": {"type": "string", "pattern": "^[A-Z]{2}-[A-Z0-9]{1,3}$"}}, ["country"]),
            "note": {"type": "string"}}, ["id", "type"])},
        "charges": {"type": "array", "items": {"$ref": "#/$defs/charge"}},
        "no_charge": obj({"description": {"type": "string", "minLength": 1}, "sources": {"type": "array", "minItems": 1, "items": ID}},
                         ["description", "sources"]),
        "rules": {"type": "array", "items": rule},
        "coverage": {"type": "array", "minItems": 1, "items": obj({
            "scope": ID, "status": {"enum": ["complete", "partial", "unpriced"]}, "reason": {"type": "string"}},
            ["scope", "status"])},
        "extensions": {"type": "object", "propertyNames": {"pattern": "^[a-z0-9-]+(\\.[a-z0-9-]+)+$"}}},
        ["orct", "dataset", "sources", "tax", "liable_vehicles", "vehicle_class_sets", "charge_objects", "charges", "coverage"]),
    # 6.13: a dataset with no_charge has no charge objects, charges or rules;
    # one without has at least one charge and one vehicle class set.
    "if": {"required": ["no_charge"]},
    "then": {"properties": {"charge_objects": {"maxItems": 0}, "charges": {"maxItems": 0}, "rules": {"maxItems": 0}}},
    "else": {"properties": {"charges": {"minItems": 1}, "vehicle_class_sets": {"minItems": 1}}},
    "$defs": {"criteria": criteria, "geometry": geometry, "place": place, "charge": charge}}

usage = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-usage-0.3.schema.json",
    "title": "ORCT 0.3 usage",
    **obj({
        "orct_usage": {"const": "0.3"},
        "vehicle": obj({"mass_kg": {"type": "integer"}, "train_mass_kg": {"type": "integer"}, "axles": {"type": "integer"},
                        "trailer_mass_kg": {"type": "integer"}, "trailer_axles": {"type": "integer"},
                        "load_capacity_kg": {"type": "integer"}, "load_kg": {"type": "number", "minimum": 0}, "train_axles": {"type": "integer"}, "length_m": {"type": "number"}, "train_length_m": {"type": "number"},
                        "height_m": {"type": "number"}, "first_axle_height_m": {"type": "number"}, "width_m": {"type": "number"},
                        "euro_class": {"enum": EURO}, "co2_class": {"type": "integer", "minimum": 1, "maximum": 5},
                        "energy": {"enum": ENERGY}, "category": {"enum": CATEGORY}, "trailer": {"type": "boolean"}}),
        "payment": {"type": "array", "items": {"enum": ["electronic", "account", "card", "cash"]}},
        "user_classes": {"type": "object", "additionalProperties": {"type": "array", "items": ID}},
        "prior_uses": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}}},
        "events": {"type": "array", "items": obj({
            "dataset": ID, "object": ID, "time": {"type": "string", "format": "date-time"},
            "role": {"enum": ["entry", "exit", "pass"]}, "km": {"type": "number", "minimum": 0},
            "overlays": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}}},
            ["dataset", "object", "time"])},
        "quantities": {"type": "array", "items": obj({
            "dataset": ID, "object": ID, "unit": {"enum": ["t_co2", "litre", "kg", "kwh"]}, "value": DEC,
            "time": {"type": "string", "format": "date-time"}}, ["dataset", "object", "unit", "value", "time"])}},
        ["orct_usage", "vehicle"])}

statement = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-statement-0.3.schema.json",
    "title": "ORCT 0.3 charge statement",
    **obj({
        "orct_statement": {"const": "0.3"},
        "complete": {"type": "boolean"},
        "lines": {"type": "array", "items": obj({
            "dataset": ID, "charge": ID, "component": {"enum": COMPONENTS},
            "objects": {"type": "array", "items": ID}, "row": {"type": "integer", "minimum": 0},
            "quantity": DEC, "unit": {"type": "string"}, "rate": DEC, "amount": DEC,
            "currency": {"type": "string", "pattern": "^[A-Z]{3}$"}, "tax_basis": {"enum": ["included", "excluded", "not_applicable", "unknown"]},
            "tax_rate": DEC, "basis": {"enum": ["official", "transcribed", "derived", "estimated"]}, "dataset_version": {"type": "string"},
            "sources": {"type": "array", "items": ID}, "notes": {"type": "array", "items": {"type": "string"}}},
            ["dataset", "charge", "component", "objects", "quantity", "unit", "amount", "currency", "tax_basis", "basis"])},
        "totals": {"type": "array", "items": obj({"currency": {"type": "string", "pattern": "^[A-Z]{3}$"}, "amount": DEC}, ["currency", "amount"])},
        "issues": {"type": "array", "items": obj({"code": {"type": "string"}, "message": {"type": "string"},
                                                  "dataset": {"type": "string"}, "charge": {"type": "string"}}, ["code", "message"])}},
        ["orct_statement", "complete", "lines", "totals", "issues"])}
for name, s in (("orct-0.3", dataset), ("orct-usage-0.3", usage), ("orct-statement-0.3", statement)):
    json.dump(s, open(f"schema/{name}.schema.json", "w"), indent=1)
print("ok")
