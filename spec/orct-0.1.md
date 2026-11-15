# Open Road Charge Tariff (ORCT) 0.1 — draft

Status: draft for discussion. The keywords MUST, SHOULD and MAY are used as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 1. Scope

ORCT describes the published charges for using roads and the rule for
computing them for one vehicle trip: tolls, vignettes, zone and congestion
charges, external-cost charges (air, noise, CO2) and carbon prices on fuel.

It does not cover payment, enforcement or on-board unit configuration. Those
stay with [ISO 17575-3](https://www.iso.org/standard/64163.html) (context
data) and [ISO 12855](https://www.iso.org/standard/88211.html) (back-office
exchange). ORCT reuses their concepts: a toll context, tariff determinants
(vehicle parameters, time classes) and section, area and cordon charging.

Why a new format: see [docs/background.md](../docs/background.md).

## 2. Dataset

One JSON document per charging scheme and validity period. Its fields:

| Field | Required | Content |
| --- | --- | --- |
| `orct_version` | yes | `"0.1"` |
| `dataset` | yes | Header, §2.1 |
| `sources` | yes | Where the figures come from, §2.2 |
| `vehicles` | yes | Which vehicles the scheme charges, §2.3 |
| `classes` | yes | The scheme's vehicle classes, §2.4 |
| `network` | yes | Where charges apply, §2.5 |
| `charges` | yes | What is charged, §3 |
| `modifiers` | no | Rules that change charges, §4 |
| `tax` | yes | Whether the figures include tax, §2.6 |
| `coverage` | yes | What the dataset does not price, §2.7 |
| `extensions` | no | Data not yet expressible in ORCT, under `x-<name>` keys, §2.8 |

### 2.1 `dataset`

`id` (unique, stable), `scheme` (the id without the validity date),
`country` (ISO 3166-1 alpha-2), `region` (ISO 3166-2, if the scheme is
regional), `currency` (ISO 4217), `valid_from` and `valid_to` (inclusive,
`YYYY-MM-DD`; no `valid_to` = until replaced), `name`, `method` (the legal
basis and the rule as the sources state it, in words), `publisher`, and
`derived_from` (for data converted from another format: repository, path,
commit).

### 2.2 `sources`

`id`, `title`, `url`; MAY add `legal_act` ([ELI](https://eur-lex.europa.eu/eli-register/about.html)
where one exists), `retrieved`, `sha256`. Every charge MUST cite at least one
source id in `sources`.

### 2.3 `vehicles`

`description`, `min_mass_kg` (lighter vehicles pay nothing), `axle_basis`:
`combination` (default: the vehicle with its trailer) or `motor_vehicle`.

### 2.4 `classes`

Each class has an `id`, an optional `label` (the scheme's own name, such as
"5" or "B"), and `criteria`. A vehicle is in a class when it meets every
criterion given:

| Criterion | Form |
| --- | --- |
| `mass_kg` | `{"min": n, "max": n}`, technically permissible maximum mass, both inclusive |
| `axles` | `{"min": n, "max": n}`, counted on `vehicles.axle_basis` |
| `length_m` | `{"over": x, "max": x}` |
| `euro` | list of Euro emission standards (0–6; EEV counts as 5) |
| `co2_class` | list of CO2 emission classes 1–5 (Directive 1999/62 art. 7ga) |

The class `any` matches every charged vehicle. Where a charge's rates are
keyed by several classes a vehicle meets, the first listed in `classes` wins.

### 2.5 `network`

Each element has an `id`, a `kind` and what locates it:

| `kind` | Located by |
| --- | --- |
| `road_class` | `road_type` (`motorway`, `other`), optional `area` (`suburban`, `interurban`), or a `description` (e.g. "all toll motorways") |
| `operator` | `operator`, optional `ref` and `label` (a stretch of that operator's road) |
| `station` | `geometry` (GeoJSON Point or MultiPoint: its junctions or booths), optional `headings` and `point_names`. A station the tariff prices but no source places has no `geometry`: its pairs are kept and listed as `partial` in `coverage` |
| `point` | `geometry` (Point), optional `heading` (the paying direction, degrees from north; none = both) |
| `section` | `from` and `to` (places: `geometry`, optional `name` and `heading`), optional `road` and `km` (official length) |
| `stretch` | `geometry` (LineString through its junctions in order), optional `point_names` |
| `zone` | `geometry` (Polygon or MultiPolygon, [lon, lat]) |

Elements MAY add `osm` (OpenStreetMap references) and `match_km` (how close a
route must pass to use the element).

### 2.6 `tax`

`included`: `true`, `false` or `null` (the sources don't say, or the dataset
doesn't record it). MAY add `rate` and `name`. A calculator MUST report the
tax basis of every line; with `null` it reports it as unknown.

### 2.7 `coverage`

A list of `{"scope": …, "status": "complete" | "partial" | "unpriced", "reason": …}`.
`scope` is a network id, a charge id, or `"dataset"`. A dataset with nothing
missing says `[{"scope": "dataset", "status": "complete"}]`.

### 2.8 `extensions`

Keys MUST start with `x-`. A dataset that keeps charging rules in an extension
MUST list them in `coverage` as `partial`, so a calculator that ignores the
extension knows its total can be incomplete.

## 3. Charges

Every charge has `id`, `type`, `component`, `applies_to` (network ids), `sources`,
`rates`, and MAY have `valid_from` / `valid_to` (narrower than the dataset's)
and `name`.

`component` is one of `infrastructure`, `toll` (infrastructure where the
source doesn't split it), `congestion`, `air`, `noise`, `air_noise`, `co2`,
`carbon_price`, `access` (a zone's entry or day charge), or `x-<name>`.

`rates` maps a class id to a **rate**: a number, or an object of variants
`{"default": n, "<variant>": n, …}` where each other variant applies when the
modifier that names it holds (§4).

### 3.1 The six types

| `type` | Price | Extra fields |
| --- | --- | --- |
| `distance` | rate × km on the `applies_to` elements | — |
| `od_matrix` | the pair's rate, for the entry and exit stations used | `pairs`, `directed`, `pairing` |
| `point` | rate per passage of the element | — |
| `period` | rate per period started | `period` (`day`), `day_basis` (`calendar`, `24h`) |
| `zone` | rate per day the vehicle is in the zone | `excludes` (network ids cut out of the zone) |
| `quantity` | rate × quantity | `unit` (`tonne_km` of maximum mass, `t_co2`, `litre`), `max_mass_kg` (the mass cap for `tonne_km`) |

For `od_matrix`, `rates` is empty and `pairs` lists `{"entry": station id,
"exit": station id, "rates": {class: rate}}`. Without `directed: true` a
pair prices both directions. `pairing` is `single_ticket` (one pair from the
first to the last station used, the default) or `chain` (consecutive
published pairs covering the most of the trip). A class's `fallback` (a class
id) gives a pair's rate where it has none for that class.

## 4. Modifiers

`{"kind": …, "applies_to": [charge ids], "params": {…}}`. Kinds:

| `kind` | `params` | Effect |
| --- | --- | --- |
| `variant` | `name`, and one of `hours` (`["HH:MM","HH:MM"]`), `season` (`months`, `weekdays` 0=Sunday, `easter_from`/`easter_to` days), `payment` (`"electronic"`) | the rate's named variant applies when it holds |
| `free_hours` | `hours` | nothing is charged then |
| `charging_hours` | `weekdays`, `weekends` (hours), `no_charge` (`["MM-DD","MM-DD"]`) | charged only then |
| `discount` | `name`, `percent`, and any of `classes`, `euro`, `co2_class`, `payment` | percent off for the vehicles it names, added up over those that apply |
| `exemption` | `co2_class`, `until`, `note` | no charge for those vehicles until the date |
| `factor` | `stretch` (network id), `factor` | multiplies the per-km rate on the stretch |
| `passage_group` | `group`, `minutes` | after a paid passage, the group's other elements are free for that long |
| `included_in` | `charge` | a trip paying that charge doesn't pay this one again |
| `cap` | `per` (`day`), `amount`, optional `high_season` | the most charged in the period |
| `time_schedule` | `schedule`: `[{"from": "HH:MM", "to": "HH:MM", "amount": n, "high": n}]` | the charge is the amount at the time of passage (`high` in high season) |
| `multi_pass` | `minutes`, `pays` (`highest`) | passages within that time of a charged one pay once |
| `assumed_share` | `of` (`motorway`, `suburban`), `share`, `road_type` | when the route doesn't say, that share of the km is priced on the matching rows |
| `rounding` | `to` (e.g. 0.1), `per` (`pair`, `passage`, `trip`) | how the source rounds |

Variant names in use: `electronic`, `night`, `peak`, `high_season`, and combinations such as `night_electronic`. A variant with no `variant` modifier saying when it holds is listed in `coverage` as `partial`.

Unknown kinds MUST be reported by a calculator as unapplied rules.

## 5. Calculation

Input: a route matched to the network (the elements used, in order, with km
and times), a vehicle (mass, axles, motor-vehicle axles, length, Euro
standard, CO2 class, payment medium) and a date.

1. **Select** the datasets valid on the trip date for every scheme the route
   touches, and within them the charges valid that day.
2. **Classify** the vehicle in each dataset (§2.4). No class: the scheme is
   unpriced for this vehicle. Below `min_mass_kg`: no charge.
3. **Segment** the route by the charges' `applies_to`. Where a `distance`
   charge on an `operator` element with a `label` and one without both apply,
   the more specific wins; an operator element wins over a `road_class`.
4. **Price** each charge by its type (§3.1).
5. **Apply modifiers** in this order: `exemption`, `free_hours` and
   `charging_hours`, `variant`, `included_in`, `passage_group`, `discount`,
   `factor`, `time_schedule`, `multi_pass`, `cap`, `rounding`.
6. **Tax**: keep each line's basis from `tax`.
7. **Report** one line per charge with its source ids, the totals per
   currency and component, and `complete: false` if the route touches a
   `partial` or `unpriced` scope, an extension the calculator ignored, or an
   unknown modifier.

## 6. Conformance

A dataset conforms if it validates against
[schema/orct-0.1.schema.json](../schema/orct-0.1.schema.json) and every id it
refers to exists. A calculator conforms if it reproduces the test vectors in
`tests/vectors/` to the cent (to come: each a route, a vehicle, a date and
the expected lines, taken from operators' own worked examples where they
publish them).
