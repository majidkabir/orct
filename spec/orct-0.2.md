# ORCT — Open Road Charge Tariff

**Version 0.2 — Working Draft for 1.0 — 2026-11-15**

Status: working draft. It may still change in incompatible ways until 1.0.
Comments and proposals: [github.com/majidkabir/orct/issues](https://github.com/majidkabir/orct/issues).
Licence: this text CC BY 4.0; schemas and tools MIT.

## Contents

- Introduction
- 1 Scope
- 2 Normative references
- 3 Terms and definitions
- 4 Conformance
- 5 Model overview
- 6 Dataset
- 7 Encoding
- 8 Calculation
- 9 Usage and charge statement
- 10 Versioning and extensions
- 11 Publication
- Annex A (normative) Schemas
- Annex B (informative) Mapping to ISO 17575-3 and EN 16986
- Annex C (informative) Mapping to other standards
- Annex D (informative) Examples
- Bibliography

## Introduction

Road charges are published as legal texts, PDF tables, images and web
calculators. Toll chargers exchange tariff data with their service providers
in the formats of ISO 17575-3 and ISO 12855, but those exchanges are
contractual, encoded in ASN.1 and not public. The EU requires national access
points to offer tolled roads and their charges, yet the DATEX II profile for
them has no tariff model. Everyone who prices a trip, from route planners to
emission and cost accounting, rebuilds each scheme by hand, and two tools can
price the same trip differently.

ORCT is an open format for those tariffs and a normative method to compute
the charges of one vehicle's trip from them. It encodes the concept model of
ISO 17575-3 (charge objects; vehicle, time and user classes; tariff tables;
rounding), extends it to what ISO 17575-3 leaves out (closed entry–exit
systems, vignettes bought for a period, carbon prices on fuel), and adds
exact money, tax basis, provenance and an explicit record of what a dataset
does not cover.

The reasons for each design choice are in
[docs/decisions.md](../docs/decisions.md); the survey behind them is in
[docs/research.md](../docs/research.md).

## 1 Scope

This document specifies:

- a data format for publishing the charges for using roads: tolls, user
  charges (vignettes), access and congestion charges for zones, external-cost
  charges and carbon prices on fuel;
- a format for describing one vehicle's use of charged roads (usage);
- a normative method to compute the charges of that usage (calculation); and
- a format for the result (charge statement).

It applies to any vehicle class and any country.

It does not specify payment, enforcement, on-board equipment, communication
between toll chargers and service providers, or map matching (deriving the
charge objects a trip used from positions). Those remain with ISO 17575,
ISO 12855, ISO 14906 and EN 16986.

## 2 Normative references

The following documents are referred to in the text in such a way that some
or all of their content constitutes requirements of this document.

- IETF RFC 8259, The JavaScript Object Notation (JSON) Data Interchange Format
- IETF RFC 7493, The I-JSON Message Format
- IETF RFC 7946, The GeoJSON Format
- IETF RFC 3339, Date and Time on the Internet: Timestamps
- JSON Schema, draft 2020-12
- ISO 4217, Codes for the representation of currencies
- ISO 3166-1 and ISO 3166-2, Codes for the representation of names of countries and their subdivisions
- ISO 8601-1, Date and time — Representations for information interchange (durations)
- IANA Time Zone Database
- IETF BCP 47, Tags for identifying languages
- ISO 14906, Electronic fee collection — Application interface definition for dedicated short-range communication (vehicle attributes, clause 8.4)
- UNECE Consolidated Resolution on the Construction of Vehicles (R.E.3), vehicle categories

## 3 Terms and definitions

Terms marked † follow the definitions of ISO 17575-3:2016, clause 3.

**3.1 toll** † — charge, tax or duty levied in connection with using a vehicle in a toll domain.

**3.2 toll charger** — entity that levies a toll for the use of vehicles in a toll domain.

**3.3 toll scheme** † — organisational view of a toll regime, including its actors and their relationships.

**3.4 charge object** † — geographic or road-related object for whose use a charge is applied. ORCT's object types are in 6.9.

**3.5 tariff determinant** — property that decides the amount of a charge: the charge object, vehicle class, time class, user class or product.

**3.6 vehicle class** — set of vehicles, defined by vehicle parameters, that a scheme charges alike (ISO 17575-3: local vehicle class).

**3.7 time class** — set of instants, defined by days and times of day, that a scheme charges alike (ISO 17575-3: time class).

**3.8 user class** — set of users, defined by payment means or contract, that a scheme charges alike (ISO 17575-3: user class).

**3.9 dataset** — one ORCT document: the tariffs of one toll scheme for one validity period.

**3.10 charge** — part of a dataset that prices one kind of use (one charge type, one component) in a rate table.

**3.11 rate table** — the `columns` and `rows` of a charge: one row per combination of tariff determinants, each with an amount.

**3.12 usage** — the charge objects one vehicle used on one trip, with times and distances (clause 9.1).

**3.13 charge statement** — result of the calculation: one line per amount due (clause 9.2).

**3.14 user charge** — specified amount conferring the right to use infrastructure for a given period (Directive 1999/62/EC, Art. 2).

The verbal forms follow the ISO/IEC Directives, Part 2: "shall" is a
requirement, "should" a recommendation, "may" a permission, "can" a
possibility.

## 4 Conformance

**4.1 Dataset.** A dataset conforms if it validates against the schema in
Annex A, every identifier it refers to exists in it, and it meets every "shall"
of clauses 6 and 7.

**4.2 Producer.** A producer conforms if every dataset it publishes conforms,
every amount traces to a cited source, and `coverage` lists everything the
producer knows the dataset does not price.

**4.3 Calculator.** A calculator conforms if, for every test vector in the
conformance suite (`tests/vectors/`), its charge statement has the expected
`complete` flag, the expected totals and, where the vector lists them, the
expected lines (charge and amount), amounts compared as decimals. A calculator may implement a subset of the features in 10.3;
for a dataset that requires a feature it does not implement it shall return a
statement with `complete: false`.

## 5 Model overview

```
dataset ── scheme, toll charger, publisher, validity, currency, time zone, licence
   ├── sources ─────────────── cited by every charge
   ├── tax                     basis of every amount
   ├── liable_vehicles         who pays at all
   ├── vehicle_class_sets ──┐
   ├── time_classes ────────┤  tariff determinants
   ├── user_classes ────────┤
   ├── charge_objects ──────┘  networks, sections, stations, points, areas, jurisdictions
   ├── charges                 one rate table each: columns + rows
   ├── rules                   exemptions, discounts, caps, passage groups ...
   └── coverage                what is not priced, and why
```

A charge's rate table is ISO 17575-3's tariff table with its tariff class
definition folded in: each row is one combination of tariff determinants and
its amount.

## 6 Dataset

### 6.1 Document

A dataset is a JSON object with these members:

| Member | Req. | Content |
| --- | --- | --- |
| `orct` | yes | Specification version, `"0.2"` |
| `dataset` | yes | Header (6.2) |
| `sources` | yes | Cited documents (6.3) |
| `tax` | yes | Tax basis (6.4) |
| `liable_vehicles` | yes | Vehicles the scheme charges (6.5) |
| `vehicle_class_sets` | yes | Vehicle classes (6.6) |
| `time_classes` | no | Time classes (6.7) |
| `calendars` | no | Explicit date lists (6.7) |
| `user_classes` | no | User classes (6.8) |
| `charge_objects` | yes | What is charged for (6.9) |
| `charges` | yes | Rate tables (6.10) |
| `rules` | no | Rules on charges (6.11) |
| `coverage` | yes | What is not priced (6.12) |
| `extensions` | no | Namespaced extensions (10.2) |

Every `id` shall be unique within its list; identifiers of classes, objects,
charges and rules shall be unique within the dataset.

### 6.2 Header (`dataset`)

| Member | Req. | Content |
| --- | --- | --- |
| `id` | yes | Globally unique, stable identifier. Recommended form `<publisher>/<scheme>/<valid_from>`. |
| `version` | no | Revision of this dataset; a corrected dataset keeps `id` and increases `version`. |
| `scheme` | yes | `{id, name, country, region}`: scheme identifier, name, ISO 3166-1 alpha-2 country, ISO 3166-2 region for a regional scheme. |
| `toll_charger` | no | `{name, country, efc_provider, url}`; `efc_provider` = `{country_code, issuer_id}` as registered under ISO 14816 where one exists. |
| `publisher` | yes | `{name, role, url}`; `role` is `toll_charger`, `authority` or `third_party`. |
| `valid_from`, `valid_to` | yes, no | Inclusive local dates; no `valid_to` = until replaced. |
| `currency` | yes | ISO 4217 code. |
| `timezone` | yes | IANA time zone in which times of day and dates are read. |
| `license` | yes | SPDX identifier or URL of the licence of this dataset. |
| `method` | yes | The legal basis and the charging rule in words, as the sources state them. |
| `names` | no | Name of the scheme by BCP 47 language tag. |
| `derived_from` | no | `{url, path, commit}` of data this dataset was converted from. |
| `required_features` | yes | Every feature (10.3) the dataset uses, so a calculator knows whether it can price it fully. |

### 6.3 Sources

Each source: `id`, `title`, `url`; optional `legal_act` (an ELI URI where
one exists, otherwise a citation), `retrieved` (date), `sha256` (of the
retrieved file) and `locator` (page, table or article).

### 6.4 Tax (`tax`)

`basis` shall be one of:

- `included` — amounts include the tax at `rate`;
- `excluded` — amounts exclude it; the tax at `rate` is due on top;
- `not_applicable` — the charge is not subject to the tax;
- `unknown` — the sources do not say.

`rate` is a decimal fraction (`"0.22"`); `name` the tax's name (`"IVA"`).
A charge may override the dataset's `tax` with its own.

### 6.5 Liable vehicles (`liable_vehicles`)

`{description, criteria}`. A vehicle that does not meet `criteria` (6.6.2)
owes nothing under this dataset.

### 6.6 Vehicle classes

#### 6.6.1 Parameters

Criteria shall use only these parameters. They follow ISO 14906 attributes
and registration data, the parameters Delegated Regulation (EU) 2020/203
Annex I allows for toll classification.

| Parameter | Type | Meaning | Source attribute |
| --- | --- | --- | --- |
| `mass_kg` | integer | Technically permissible maximum laden mass of the motor vehicle | ISO 14906 VehicleWeightLimits.vehicleMaxLadenWeight; registration F.1 |
| `train_mass_kg` | integer | Same, of the combination; equals `mass_kg` without a trailer | vehicleTrainMaximumWeight; F.3 |
| `axles` | integer | Axles of the motor vehicle | VehicleAxles |
| `train_axles` | integer | Axles of the combination | — |
| `length_m`, `train_length_m` | number | Overall length of the vehicle, of the combination | VehicleDimensions |
| `height_m` | number | Overall height | VehicleDimensions |
| `first_axle_height_m` | number | Height measured over the first axle | VehicleAxles.vehicleFirstAxleHeight |
| `width_m` | number | Overall width | VehicleDimensions |
| `euro_class` | string | `0`–`6`, `EEV`, `7` | EnvironmentalCharacteristics.euroValue |
| `co2_class` | integer | 1–5, Directive 1999/62/EC Art. 7ga | ISO 17573-3:2024 |
| `energy` | string | `diesel`, `petrol`, `lpg`, `cng`, `lng`, `electric`, `hydrogen`, `hybrid`, `other` | EngineCharacteristics |
| `category` | string | UNECE category (`M1`…`M3`, `N1`…`N3`, `L`) | registration J |
| `trailer` | boolean | Towing a trailer or semi-trailer | — |

#### 6.6.2 Criteria

A criteria object maps parameters to conditions. A numeric condition is an
object with any of `min`, `max` (inclusive), `gt`, `lt` (exclusive). A string
condition is an array of allowed values. A boolean condition is `true` or
`false`. `any_of` is an array of two or more criteria objects, for a law that
names alternatives ("Euro VI, or electric or hydrogen"); it holds if any of
them is met. An empty object matches every vehicle.

A vehicle meets the criteria if every condition holds, and does not meet them
if any condition fails. `any_of` holds if one of its criteria is met, fails if
all of them fail, and is unknown otherwise. If no condition fails but one is
unknown, because the vehicle's description lacks a parameter it tests, the
result is unknown: a calculator shall not assume a value. A use whose row
selection depends on it is unpriced, and a rule whose criteria depend on it
makes the statement incomplete (8.9).

#### 6.6.3 Class sets

`vehicle_class_sets` is a list of `{id, name, classes}`; each class is
`{id, label, criteria, fallback}`. A vehicle belongs to at most one class per
set: the first, in list order, whose criteria it meets. `fallback` names a
class of the same set whose rows apply where a row for this class is missing.
A dataset may hold several sets, for example a closed system's own groups
beside the network's classes.

### 6.7 Time classes and calendars

A time class is `{id, label, days, times, defined, note}`.

`days` is a list of day selectors; a day is selected if any of them selects
it. Without `days` every day is selected. A day selector has these members,
all optional:

- `weekdays`: ISO weekday numbers, 1 = Monday … 7 = Sunday;
- `months`: 1–12;
- `dates`: `MM-DD` (every year) or `YYYY-MM-DD`;
- `date_ranges`: pairs `[from, to]`, inclusive, both `MM-DD` (may wrap past the year's end) or both `YYYY-MM-DD`;
- `easter`: pairs `[from, to]` of day offsets from Easter Sunday (Gregorian);
- `calendars`: identifiers of calendars;
- `exclude`: a day selector (without `exclude`) of days removed.

A selector selects a day if its weekday is in `weekdays` (when given), its
month is in `months` (when given), it is in the union of `dates`,
`date_ranges`, `easter` and `calendars` (when any of them is given), and
`exclude` does not select it. So "weekends in summer" is one selector
(`weekdays` and `months`), and "summer or weekends" is two.

`times` is a list of local intervals `[start, end]`, `HH:MM`, start
inclusive, end exclusive, `24:00` allowed as end. An interval with
`end` ≤ `start` crosses midnight and belongs to the day on which it starts.
Without `times` the class covers whole days. An instant is in the class if it
falls in an interval of a selected day, read in the dataset's `timezone`.

`defined: false` marks a time class the sources name but do not define (for
example a rush hour without its hours); rows using it can't be applied, and
`coverage` shall list it.

A calendar is `{id, name, dates, covers_to}`: explicit `YYYY-MM-DD` dates
(public holidays, for instance) and the last date the list is complete for.
An instant after `covers_to` in a time class that uses the calendar makes the
result incomplete.

### 6.8 User classes

A user class is `{id, label, payment, note}`. `payment` lists payment means
that make a user a member: `electronic` (on-board equipment or a contract with
the toll charger or a service provider), `account`, `card`, `cash`. A usage
names the user classes it holds or the payment means it uses (9.1).

### 6.9 Charge objects

| Member | Content |
| --- | --- |
| `id`, `type` | `type` is `network`, `section`, `station`, `point`, `area` or `jurisdiction`. |
| `parents` | Objects that contain this one. Rows for a parent apply to its descendants (6.10.3). An object may have several parents when a network is divided on several dimensions at once: a km on a suburban motorway belongs to both "motorways" and "suburban roads". Parents shall not form a cycle. |
| `name`, `names`, `code` | Name, names by language, the operator's own code. |
| `operator`, `road` | Operator and road reference (`A4`, `E45`). |
| `network` | For `network`: `{road_types, area, description}`; `road_types` from `motorway`, `trunk`, `other`; `area` `suburban` or `interurban`. |
| `from`, `to`, `length_km` | For `section`: end places (each `{name, geometry, heading}`) and official length. |
| `location` | `{geometry, openlr, osm, heading, match_m, headings, point_names}`: RFC 7946 geometry in WGS 84; an OpenLR reference (base64); OpenStreetMap references (informative); the paying direction in degrees from north (none = both); how near a route must pass, in metres; for a MultiPoint, the heading and name of each point. |
| `jurisdiction` | For `jurisdiction`: `{country, region}`. |

A station, point or area shall have a `location.geometry`, and a section a
`geometry` in both `from` and `to` (or a `location.geometry`), unless no source
locates it; then it shall have none, and its
id shall be a `scope` in `coverage`. Networks and jurisdictions are described
by their attributes and need no geometry.

### 6.10 Charges

#### 6.10.1 Members

| Member | Req. | Content |
| --- | --- | --- |
| `id`, `name` | yes, no | |
| `type` | yes | `distance`, `section`, `od`, `point`, `area`, `period`, `quantity` (6.10.2). |
| `component` | yes | What the charge pays for: `infrastructure`, `air_pollution`, `noise`, `air_pollution_noise`, `co2`, `congestion`, `markup`, `access`, `carbon_price`, `unspecified`, `other`. The first six follow Directive 1999/62/EC. |
| `component_label` | no | The source's own name for the component. |
| `unit` | yes | What one amount is per (6.10.2). |
| `columns` | yes | Names of the row members, in order (6.10.3). |
| `rows` | yes | Arrays aligned with `columns`. |
| `objects` | cond. | The charge objects the charge applies to, required when `columns` has no `object` (nor `entry`/`exit`). |
| `sources` | yes | Source ids, at least one. |
| `basis` | yes | `official` (published as data by the toll charger), `transcribed` (copied from an official document), `derived` (computed from official figures), `estimated`. |
| `unmatched` | no | `unpriced` (default): a use with no matching row is unpriced; `free`: it costs nothing. |
| `time_basis` | no | Which instant selects the time class: `entry` (default for `od`), `exit`, `event` (default otherwise). |
| `rounding` | no | `{increment, mode, stage}`; `mode` `half_up`, `half_even`, `up`, `down`; `stage` `line`, `charge`, `statement` (8.7). |
| `tax` | no | Overrides the dataset's `tax`. |
| `valid_from`, `valid_to` | no | Narrower validity than the dataset's. |
| `method` | no | Rule in words, where it differs from the dataset's. |

#### 6.10.2 Types

| `type` | Prices | `unit` | Type-specific members |
| --- | --- | --- | --- |
| `distance` | km driven on networks | `km`, or `tkm` (per tonne of mass per km) | `mass_basis` (parameter, default `train_mass_kg`), `mass_cap_kg` |
| `section` | each use of a section | `use`, or `km` (per km of its official length) | — |
| `od` | each trip in a closed system, by entry and exit station | `trip` | `directed` (default `false`: a pair prices both directions), `pairing` (`single_ticket` default, or `chain`) |
| `point` | each passage of a point | `passage` | — |
| `area` | each day in a zone, or each entry | `day`, `entry` | — |
| `period` | each period product (a vignette) | `product` | `day_basis` (`calendar` default, or `rolling`) |
| `quantity` | a quantity used in a jurisdiction | `t_co2`, `litre`, `kg`, `kwh` | — |

#### 6.10.3 Columns and rows

`columns` shall contain `amount` and may contain:

| Column | Value |
| --- | --- |
| `object` | charge object id (not for `od`) |
| `entry`, `exit` | station ids (only and both for `od`) |
| `vehicle_class` | vehicle class id, from any set |
| `time_class` | time class id |
| `user_class` | user class id |
| `product` | ISO 8601 duration (`P1D`, `P10D`, `P1M`, `P1Y`), only for `period` |
| `priority` | integer, default 0 |
| `amount` | decimal string (7.2) |

A key value of `null` means "any". Rows shall not repeat the same combination
of key values.

**Row selection.** For one use, a row matches when every key holds:

- `object`, `entry`, `exit`: the used object, or one of its ancestors (reached through `parents`);
- `vehicle_class`: the vehicle's class in that class's set, or a class reached through `fallback` from it;
- `time_class`: a time class containing the instant (6.7, `time_basis`);
- `user_class`: a user class the user holds;
- `product`: the product being priced;
- `null`: anything.

Of the matching rows the one selected is:

1. Keep the rows with the highest `priority`.
2. Compare them column by column, in the order of `columns`; the first column
   in which they differ decides. In a column, the use's own value beats one
   reached through parents or fallback, an ancestor fewer parent steps away
   (on the shortest path) beats one more steps away, and any value beats
   `null`.

If rows still tie because the user holds several matching user classes, the
lowest amount applies. Any other tie makes the dataset non-conforming, for
example two rows keyed by two parents of the same object, at the same
distance, that differ in nothing else.

### 6.11 Rules

A rule is `{id, kind, applies_to, params}`; `applies_to` lists charge ids.
Every kind's `params` may have a `note`. The members the table marks "when
given" or "any of", `objects` of `included_in` and `time_class` of `cap` are
optional; the others are required.

| `kind` | `params` | Effect |
| --- | --- | --- |
| `exemption` | `criteria`, `from`, `until`, `note` | Vehicles meeting `criteria` owe nothing, between the dates when given. |
| `included_in` | `charge` (an `od` charge), `objects` | A use of the listed objects (all, when not given) between the entry and exit times of a trip priced by that charge is not charged again. |
| `passage_group` | `objects`, `minutes`, `pays` (`first` or `highest`) | Only passages of the group's objects with an amount above zero count. A run starts at such a passage; those less than `minutes` after it belong to the run, and the run pays once: the first passage's amount, or the highest. The next one after that starts a new run. A free passage starts no run. |
| `factor` | `object`, `factor` | Km the usage attributes to `object` (a stretch) are priced at the rate times `factor`. |
| `discount` | `name`, `percent`, and any of `criteria`, `user_class`, `payment` | Percent off for the matching vehicles or users. The percentages of all discounts that apply to a use are added, then taken off once (10 % and 20 % make 30 %). |
| `minimum` | `per` (`trip`), `amount` | The charges' total for a trip is at least `amount`. |
| `cap` | `per` (`day`, `month`, `trip`), `amount`, `time_class` | The charges' total in each period is at most `amount`. With `time_class`, only the lines whose time is in the class count and are capped. |

### 6.12 Coverage

A list of `{scope, status, reason}`: `scope` is `dataset` or the id of an
object, class, charge or rule; `status` is `complete`, `partial` or
`unpriced`. A dataset with nothing missing shall state
`[{"scope": "dataset", "status": "complete"}]`.

## 7 Encoding

**7.1 JSON.** A dataset is an I-JSON (RFC 7493) text in UTF-8. File names
should end in `.orct.json`; the proposed media type is
`application/vnd.orct+json`.

**7.2 Decimals.** Every amount, rate, percentage, factor and tax rate is a
string matching `^-?[0-9]+(\.[0-9]+)?$`. Calculators shall use exact decimal
arithmetic. Measurements (mass, length, km in usage) may be JSON numbers.

**7.3 Dates and times.** Dates `YYYY-MM-DD`; instants in usage RFC 3339 with
offset; times of day `HH:MM`; durations ISO 8601.

**7.4 Geometry.** An RFC 7946 GeoJSON geometry object of type `Point`,
`MultiPoint`, `LineString`, `MultiLineString`, `Polygon` or `MultiPolygon`,
`[longitude, latitude]` in WGS 84.

**7.5 Identifiers.** Case-sensitive strings without leading or trailing
spaces.

## 8 Calculation

**8.1 Inputs.** One or more datasets, one usage (9.1).

**8.2 Applicability.** For each event of the usage, the dataset applies if
the event's local date is within its validity; a charge applies if, in
addition, the date is within the charge's own validity. A vehicle that does
not meet `liable_vehicles` owes nothing under the dataset.

**8.3 Classification.** The vehicle is classified in every class set (6.6.3).

**8.4 Uses per charge type.**

- `distance`: each event on an object the charge applies to (directly or through an ancestor) is one use; the quantity is its km, or for `tkm` km × min(mass, `mass_cap_kg`) / 1000 with the mass from `mass_basis`.
- `section`: each event on a section is one use; for unit `km` the quantity is the section's `length_km`.
- `point`: each event on a point is one use.
- `od`: the events on the charge's stations, in time order, form trips: a trip starts at an event with role `entry` (or the first station event) and ends at the next event with role `exit` (or the last). With `single_ticket` one use is priced from the trip's first to its last station. With `chain` the trip is split: from the first station, take the farthest later station of the trip for which a row matches, price that pair, and continue from it.
- `area`: unit `day`: each local date with at least one event in the area is one use, priced at the highest amount any of that date's events selects (a date whose events select no row costs nothing if `unmatched` is `free`); unit `entry`: each event with role `entry`.
- `period`: the local dates (`day_basis` `calendar`, the default) or instants (`rolling`) of the events on the charge's objects are covered by the set of products whose total is lowest; each product bought is one use. A product with duration D bought for date or instant s covers from s up to, not including, s + D, where months and years end on the same day of the month, or on the month's last day when it has no such day, and weeks count 7 days.
- `quantity`: each quantity of the usage for the charge's objects is one use.

**8.5 Amount of a use.** Select the row (6.10.3). No row: the use is
unpriced, or free if `unmatched` is `free`. Otherwise the amount is the row's
amount times the quantity (1 when the unit has none).

**8.6 Rules.** Apply in this order: `exemption`, `included_in`,
`passage_group`, `factor`, `discount`, `minimum`, `cap`. A rule of a kind the
calculator does not implement makes the result incomplete. For `minimum` and
`cap`, `per: day` groups the lines of the rule's charges by the local date of
their time, `month` by local month, and `trip` takes all of them.

**8.7 Rounding.** Round as each charge's `rounding` says: `line` rounds each
use's amount, `charge` the sum per charge, `statement` the total. Without
`rounding`, amounts stay exact and the statement total per currency is rounded
half-up to the currency's minor unit.

**8.8 Tax.** Each line carries the tax basis and rate of its charge or
dataset.

**8.9 Completeness.** The statement is `complete: false` when an event lies
outside the validity of the datasets given for it; any use is unpriced; the
row that would be selected needs a time class with `defined: false` or a date
after a calendar's `covers_to`; the vehicle's class or a rule's criteria
can't be decided for a missing vehicle parameter; the usage touches a
`coverage` scope that is `partial` or `unpriced`; or a required feature or
rule kind is not implemented.

## 9 Usage and charge statement

**9.1 Usage.**

| Member | Content |
| --- | --- |
| `orct_usage` | `"0.2"` |
| `vehicle` | Vehicle parameters (6.6.1). |
| `payment` | Payment means used (6.8). |
| `user_classes` | `{dataset id: [user class ids]}` held explicitly. |
| `events` | `[{dataset, object, time, role, km, overlays}]`: one per use of a charge object, in any order; `role` is `entry`, `exit` or `pass`; `km` for networks; `overlays` `{object id: km}` for stretches inside a network. |
| `quantities` | `[{dataset, object, unit, value, time}]` |

**9.2 Charge statement.**

| Member | Content |
| --- | --- |
| `orct_statement` | `"0.2"` |
| `complete` | Boolean (8.9). |
| `lines` | `[{dataset, charge, component, objects, row, quantity, unit, rate, amount, currency, tax_basis, tax_rate, sources, notes}]`; `row` is the index of the selected row. Adjustments made by `minimum`, `cap` or rounding at the `charge` stage are lines of their own, with unit `rule`, no `row` or `rate`, and as `charge` the first charge in the rule's `applies_to` among the lines adjusted. |
| `totals` | `[{currency, amount}]` |
| `issues` | `[{code, message, dataset, charge}]`, the reasons for incompleteness and any warnings. |

## 10 Versioning and extensions

**10.1 Versions.** `orct` is `MAJOR.MINOR`. Until 1.0, any version may change
anything, without backward compatibility. From 1.0, a minor version only adds
optional members; a major version may change meaning. Readers shall ignore
unknown members, except as 10.3 says. Published datasets should not change;
corrections increase `dataset.version`.

**10.2 Extensions.** `extensions` maps reverse domain names
(`org.example.tolls`) to objects. Names without a dot and names starting with
`x-` are reserved. A dataset that keeps any part of its charging rules in an
extension shall list that part in `coverage` as `partial`.

**10.3 Features.** Feature identifiers: `type.distance`, `type.section`,
`type.od`, `type.od.chain`, `type.point`, `type.area`, `type.period`,
`type.quantity`, `time_classes`, `calendars`, `user_classes`, `rounding`,
`rule.exemption`, `rule.included_in`, `rule.passage_group`, `rule.factor`,
`rule.discount`, `rule.minimum`, `rule.cap`. A dataset shall list every
feature it uses in `required_features`.

## 11 Publication

A producer should publish a feed: an `index.json` listing each dataset's `id`,
scheme, country, validity, file and coverage status, beside the datasets. On
EU national access points, feeds should be described with mobilityDCAT-AP.
Datasets should cite legal acts by ELI.

## Annex A (normative) Schemas

- Dataset: [schema/orct-0.2.schema.json](../schema/orct-0.2.schema.json)
- Usage: [schema/orct-usage-0.2.schema.json](../schema/orct-usage-0.2.schema.json)
- Charge statement: [schema/orct-statement-0.2.schema.json](../schema/orct-statement-0.2.schema.json)

## Annex B (informative) Mapping to ISO 17575-3 and EN 16986

| ISO 17575-3 / EN 16986 element | ORCT |
| --- | --- |
| TollContextOverview / tollContextOverview (country code, provider identifier, name, version, validFrom) | `dataset` (`scheme`, `toll_charger.efc_provider`, `version`, `valid_from`) |
| TariffTable (tariffs, chargeUnit, roundingRule, version) | `charges` (`rows`, `unit`, `currency`, `rounding`) |
| TariffClassDefinition (tariff classes, defined by tariff determinants such as vehicle parameters and time classes) | the key columns of a row |
| LocalVehicleClassDefinition | `vehicle_class_sets` |
| TimeClassDefinition | `time_classes` |
| UserClassDefinition | `user_classes` |
| TollContextLayout (charge objects and their geometry) | `charge_objects` |
| Charging principles: road section, area by distance, area by time, cordon | `section`; `distance`; `period` and `area` (unit `day`); `point` (cordon points) and `area` (unit `entry`) |
| ChargeReportingEvents, reporting rules | out of scope (map matching and reporting) |
| — (DSRC closed systems) | `od` |
| ISO 12855 toll declaration, billing details | usage (9.1), charge statement (9.2) |

## Annex C (informative) Mapping to other standards

| Standard | Element | ORCT |
| --- | --- | --- |
| Directive 1999/62/EC | infrastructure, external-cost (air, noise, CO2), congestion charges; mark-up; user charge | `component`; `period` |
| Delegated Reg. (EU) 2020/203 Annex I | publication of the correspondence between classification parameters and tariff classes | `vehicle_class_sets` |
| Reg. (EU) 2022/670 | tolled roads, applicable charges, payment methods | a dataset; `user_classes` |
| NeTEx Part 3 | DistanceMatrixElement, UserProfile, TimeInterval, FareTable, Rounding | `od` rows, `vehicle_class`/`user_class`, `time_class`, rate table, `rounding` |
| GTFS Fares v2 | rider categories, timeframes, rule_priority | user classes, time classes, `priority` |
| OCPI 2.2.1 | TariffElement, PriceComponent, TariffRestrictions | row, amount, key columns |
| DATEX II | OpenLR location references, validity | `location.openlr`, time classes |

## Annex D (informative) Examples

A distance charge by mass class (illustrative values):

```json
{
  "id": "infra", "type": "distance", "component": "infrastructure", "unit": "km",
  "objects": ["federal-roads"], "basis": "transcribed", "sources": ["s1"],
  "columns": ["vehicle_class", "amount"],
  "rows": [["m1", "0.093"], ["m2", "0.110"], ["m3", "0.151"]]
}
```

A closed system with an electronic-payment price and a night tariff that
replaces both day prices (illustrative values; without `priority` the
electronic row would win at night, because `user_class` comes before
`time_class`):

```json
{
  "id": "system-a", "type": "od", "component": "infrastructure", "unit": "trip",
  "basis": "transcribed", "sources": ["s2"],
  "columns": ["entry", "exit", "vehicle_class", "user_class", "time_class", "priority", "amount"],
  "rows": [
    ["a1", "a2", "heavy2", null, null, 0, "9.40"],
    ["a1", "a2", "heavy2", "electronic", null, 0, "8.93"],
    ["a1", "a2", "heavy2", null, "night", 1, "4.70"]
  ]
}
```

A barrier free at night, everyone, overriding class rows through `priority`:

```json
{
  "columns": ["object", "vehicle_class", "time_class", "priority", "amount"],
  "rows": [["gate", "c5", null, 0, "8.40"], ["gate", null, "night", 1, "0"]]
}
```

The datasets under `data/` are full examples for 35 countries.

## Bibliography

See [docs/research.md](../docs/research.md).
