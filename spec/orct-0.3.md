# ORCT — Open Road Charge Tariff

**Version 0.3 — Working Draft for 1.0 — 2026-11-16**

## Contents

- Foreword
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
- Annex C (informative) Mapping to other standards and laws
- Annex D (informative) Examples
- Bibliography

## Foreword

This document is a working draft, maintained in the open at
[github.com/majidkabir/orct](https://github.com/majidkabir/orct), where
comments and proposals are made as issues. Until version 1.0, the first
version offered for adoption, any part of it may change without backward
compatibility (10.1). The questions raised in review, and what is still
open, are in [docs/review.md](../docs/review.md).

The text is licensed under CC BY 4.0; the schemas (Annex A), the reference
calculator and the conformance suite under the MIT licence.

This document is drafted after the ISO/IEC Directives, Part 2 [1], so that
it can be taken into a CEN or ISO deliverable.

## Introduction

Road charges are published as legal texts, PDF tables, images and web
calculators. Toll chargers exchange tariff data with their service providers
in the formats of ISO 17575-3 [2] and ISO 12855 [3], but those exchanges are
contractual, encoded in ASN.1 and not public. EU law requires the
identification of tolled roads and the applicable road user charges to be
made accessible through national access points [10], yet the DATEX II
profiles for these data have no tariff model [15]. Everyone who prices a
trip, from route planners to emission and cost accounting, rebuilds each
scheme by hand, and two tools can price the same trip differently.

ORCT is an open format for those tariffs and a normative method to compute
the charges of one vehicle's trip from them. It encodes the concept model of
ISO 17575-3 (charge objects; vehicle, time and user classes; tariff tables;
rounding), extends it to what ISO 17575-3 leaves out (closed entry–exit
systems, user charges bought for a period, carbon prices on fuel), and adds
exact money, the tax basis, provenance and an explicit record of what a
dataset does not cover.

The reasons for each design choice are in
[docs/decisions.md](../docs/decisions.md); the survey behind them is in
[docs/research.md](../docs/research.md).

## 1 Scope

This document specifies:

- a data format for publishing the charges for using roads: tolls, user
  charges (vignettes), access and congestion charges for zones, external-cost
  charges and carbon prices on fuel;
- a data format for describing one vehicle's use of charged roads (usage);
- a normative method to compute the charges of that usage (calculation); and
- a data format for the result (charge statement).

It applies to any vehicle and any country.

It does not specify payment, enforcement, on-board equipment, communication
between toll chargers and toll service providers, map matching (deriving
the charge objects a vehicle used from its positions), or tariffs set in real
time from the level of service. Those are the subject of the ISO 17575
series [2], ISO 12855 [3], ISO 14906, EN 16986 [4] and ISO/TS 21192 [6].

## 2 Normative references

The following documents are referred to in the text in such a way that some
or all of their content constitutes requirements of this document. For dated
references, only the edition cited applies. For undated references, the
latest edition of the referenced document (including any amendments) applies.

- IETF RFC 8259, *The JavaScript Object Notation (JSON) Data Interchange Format*
- IETF RFC 7493, *The I-JSON Message Format*
- IETF RFC 7946, *The GeoJSON Format*
- IETF RFC 3339, *Date and Time on the Internet: Timestamps*
- IETF BCP 47, *Tags for Identifying Languages*
- JSON Schema, draft 2020-12, *JSON Schema: A Media Type for Describing JSON Documents* and *JSON Schema Validation*
- ISO 3166-1, *Codes for the representation of names of countries and their subdivisions — Part 1: Country code*
- ISO 3166-2, *Codes for the representation of names of countries and their subdivisions — Part 2: Country subdivision code*
- ISO 4217, *Codes for the representation of currencies*
- ISO 8601-1:2019, *Date and time — Representations for information interchange — Part 1: Basic rules*
- EN ISO 14906:2018, *Electronic fee collection — Application interface definition for dedicated short-range communication*, clause 8.4
- ISO 14816, *Road transport and traffic telematics — Automatic vehicle and equipment identification — Numbering and data structure*
- Directive 1999/62/EC of the European Parliament and of the Council on the charging of vehicles for the use of road infrastructures, as amended
- UNECE, *Consolidated Resolution on the Construction of Vehicles (R.E.3)*, clause 2 (vehicle categories)
- IANA, *Time Zone Database*
- SPDX, *SPDX License List*
- TomTom, *OpenLR White Paper*, version 1.5
- NIST FIPS 180-4, *Secure Hash Standard* (SHA-256)
- IETF RFC 7515, *JSON Web Signature (JWS)*
- IETF RFC 7517, *JSON Web Key (JWK)*

## 3 Terms and definitions

For the purposes of this document, the following terms and definitions
apply. Terms marked † are those of ISO 17575-3:2016 [2], clause 3.
ISO 17573-2 [19] is the vocabulary of electronic fee collection; the
definitions below are to be aligned with it before version 1.0, and where
one differs from it, ISO 17573-2 prevails for the terms it defines.

**3.1 toll** †
charge, tax or duty levied in connection with using a vehicle in a toll domain

**3.2 toll domain**
road, road network or structure, such as a bridge or a tunnel, where tolls are collected

Note: After the definition of "EETS domain" in Directive (EU) 2019/520 [7], Art. 2.

**3.3 toll charger**
public or private entity that levies tolls for the circulation of vehicles in a toll domain

Note: After Directive (EU) 2019/520 [7], Art. 2.

**3.4 toll scheme**
tolls that one toll charger levies in one toll domain under one set of rules

**3.5 charge object** †
geographic or road-related object for the use of which a charge is applied

Note: The types of charge object are listed in 6.9.

**3.6 user charge**
specified amount conferring the right to use infrastructure for a given period

Note: After Directive 1999/62/EC, Art. 2.

**3.7 tariff determinant**
property that decides the amount of a charge: the charge object, the vehicle class, the time class, the user class, the product or the use's place in a volume period

**3.8 vehicle class**
set of vehicles, defined by vehicle parameters, that a toll scheme charges alike

Note: ISO 17575-3 calls it a local vehicle class.

**3.9 time class**
set of instants, defined by days and times of day, that a toll scheme charges alike

**3.10 user class**
set of users, defined by payment means or contract, that a toll scheme charges alike

**3.11 dataset**
one ORCT document: the tariffs of one toll scheme for one validity period

**3.12 charge**
part of a dataset that prices one kind of use in one rate table

**3.13 rate table**
`columns` and `rows` of a charge: one row per combination of tariff determinants, each with an amount

**3.14 usage**
record of the charge objects one vehicle used, with times and distances (9.1)

**3.15 event**
entry of a usage recording that the vehicle used one charge object at one instant (9.1)

**3.16 use**
what one amount of a charge is due for, derived from the events as 8.4 specifies: a distance on a network, a use of a section, a passage of a point, a trip, a day or entry in an area, a product, or a quantity

**3.17 trip**
journey through a closed system from an entry station to an exit station

**3.18 product**
user charge for one duration, such as a day or a year

**3.19 charge statement**
result of the calculation (9.2)

**3.20 line**
one amount of a charge statement: the amount due for one use, or an adjustment made by a rule or by rounding

**3.21 producer**
party that publishes datasets

**3.22 calculator**
implementation of the calculation of clause 8

## 4 Conformance

**4.1 Verbal forms and notation.** "Shall" indicates a requirement, "should"
a recommendation, "may" a permission and "can" a possibility. Member names
are in `code` font. In member tables, "Req." says whether a member is
required; members not marked required are optional. Unless given as
examples, the values a member's description lists are all its allowed
values.
Cross-references in parentheses, such as (6.6.2), point to the clause that
specifies the item.

**4.2 Dataset.** A dataset conforms if it validates against the dataset
schema of Annex A, every identifier it refers to exists in it, and it meets
every requirement of clauses 6 and 7.

**4.3 Producer.** A producer conforms if every dataset it publishes conforms,
every amount traces to a source the dataset cites, and `coverage` lists
everything the producer knows the dataset does not price.

**4.4 Calculator.** A calculator conforms if, for every test vector of the
conformance suite ([tests/vectors/](../tests/vectors/)), it returns a charge
statement that validates against the statement schema of Annex A and has the
expected `complete` value, the expected totals and, where the vector lists
them, the expected lines (charge and amount) and issue codes. Amounts are
compared as decimals. A calculator may implement a subset of the features of
10.3; for a dataset that requires a feature it does not implement, it shall
return a statement with `complete: false`.

## 5 Model overview

This clause is informative.

```
dataset ── scheme, toll charger, publisher, validity, currency, time zone, licence
   ├── sources ─────────────── cited by every charge
   ├── tax                     basis of every amount
   ├── liable_vehicles         who pays at all
   ├── vehicle_class_sets ──┐
   ├── time_classes ────────┤  tariff determinants
   ├── user_classes ────────┤
   ├── charge_objects ──────┘  networks, sections, stations, points, areas, jurisdictions
   ├── calendars               explicit dates that time classes use
   ├── charges                 one rate table each: columns + rows
   ├── rules                   exemptions, discounts, caps, passage groups ...
   ├── coverage                what is not priced, and why
   └── no_charge               or: that the area charges nothing, and on whose word
```

A charge's rate table is ISO 17575-3's tariff table with its tariff class
definitions folded in: each row is one combination of tariff determinants and
its amount. A calculator turns the events of a usage into uses (8.4), selects
one row per use (6.10.3), applies the rules (8.6) and rounds (8.7). A dataset
with `no_charge` (6.13) has no charges: it states, with its sources, that the
area charges nothing.

## 6 Dataset

### 6.1 Document

A dataset is a JSON object with these members:

| Member | Req. | Content |
| --- | --- | --- |
| `orct` | yes | Specification version, `"0.3"`. |
| `dataset` | yes | Header (6.2). |
| `sources` | yes | Cited documents (6.3). |
| `tax` | yes | Tax basis (6.4). |
| `liable_vehicles` | yes | Vehicles the toll scheme charges (6.5). |
| `vehicle_class_sets` | yes | Vehicle classes (6.6). |
| `time_classes` | no | Time classes (6.7). |
| `calendars` | no | Explicit date lists (6.7). |
| `user_classes` | no | User classes (6.8). |
| `charge_objects` | yes | What is charged for (6.9); empty with `no_charge`. |
| `charges` | yes | Rate tables (6.10); at least one, none with `no_charge`. |
| `rules` | no | Rules on charges (6.11). |
| `coverage` | yes | What is not priced (6.12). |
| `no_charge` | no | That the scheme's area charges nothing (6.13). |
| `extensions` | no | Namespaced extensions (10.2). |

Every identifier (`id`) of a source, vehicle class set, vehicle class, time
class, calendar, user class, charge object, charge or rule shall be unique
within the dataset.

### 6.2 Header (`dataset`)

| Member | Req. | Content |
| --- | --- | --- |
| `id` | yes | Globally unique, stable identifier of the dataset. It should have the form `<publisher>/<scheme>/<valid_from>`. |
| `version` | no | Revision of the dataset; a corrected dataset keeps `id` and increases `version`. |
| `scheme` | yes | `{id, name, country, region}`: identifier and name of the toll scheme (both required), ISO 3166-1 alpha-2 country (required), ISO 3166-2 subdivision for a regional scheme. |
| `toll_charger` | no | `{name, country, url, efc_provider}`: name (required), ISO 3166-1 alpha-2 country and web site of the toll charger; `efc_provider` is `{country_code, issuer_id}`, the toll charger's identifier registered under ISO 14816, where it has one. |
| `publisher` | yes | `{name, role, url}`; `name` and `role` are required; `role` is `toll_charger`, `authority` or `third_party`. |
| `valid_from` | yes | First local date the dataset applies to. |
| `valid_to` | no | Last local date the dataset applies to; without it, the dataset applies until replaced. |
| `currency` | yes | ISO 4217 code of every amount. |
| `timezone` | yes | IANA time zone in which local dates and times of day are read. |
| `license` | yes | SPDX licence identifier or URL of the dataset's licence. |
| `method` | yes | The legal basis and the charging rule in words, as the sources state them. |
| `names` | no | Name of the toll scheme by BCP 47 language tag. |
| `derived_from` | no | `{url, path, commit}` of the data the dataset was converted from; `url` is required. |
| `efc_context` | no | `{standard, version, valid_from}`: the EFC context data the toll charger gives its toll service providers, from which this dataset was generated; `standard` is `ISO 17575-3`, `EN 16986` or `ISO 12855`, and `version` the context data's version (both required). Where amounts differ, the context data prevails for billing. |
| `required_features` | yes | Every feature (10.3) the dataset uses. |

### 6.3 Sources (`sources`)

| Member | Req. | Content |
| --- | --- | --- |
| `id` | yes | Identifier, cited by charges. |
| `title` | yes | Title of the document. |
| `url` | yes | Where the document is published. |
| `legal_act` | no | The act, as an ELI URI [17] where one exists, otherwise as a citation. |
| `retrieved` | no | Date the document was retrieved. |
| `sha256` | no | SHA-256 of the retrieved file, in hexadecimal. |
| `locator` | no | Page, table or article the amounts come from. |

### 6.4 Tax (`tax`)

| Member | Req. | Content |
| --- | --- | --- |
| `basis` | yes | `included`: amounts include the tax; `excluded`: amounts exclude it and the tax is due on top; `not_applicable`: the charge is not subject to the tax; `unknown`: the sources do not say. |
| `rate` | no | The tax rate as a decimal fraction (`"0.25"`), where the sources give it. |
| `name` | no | The tax's name (`"VAT"`). |
| `note` | no | Remarks. |

A charge may state its own `tax`, which then replaces the dataset's for that
charge.

### 6.5 Liable vehicles (`liable_vehicles`)

`{description, criteria}`; `criteria` (6.6.2) is required. A vehicle that
does not meet `criteria` owes nothing under the dataset.

### 6.6 Vehicle classes

#### 6.6.1 Parameters

Criteria and usages shall use only these parameters. They follow the vehicle
attributes of EN ISO 14906:2018, clause 8.4, and the registration data that
Delegated Regulation (EU) 2020/203 [8], Annex I, allows toll chargers to
classify by.

| Parameter | Type | Meaning | Source attribute |
| --- | --- | --- | --- |
| `mass_kg` | integer | Technically permissible maximum laden mass of the motor vehicle, in kg | VehicleWeightLimits.vehicleMaxLadenWeight; registration F.1 [11] |
| `train_mass_kg` | integer | Maximum permissible laden mass of the whole vehicle combination, in kg; equals `mass_kg` without a trailer | VehicleWeightLimits.vehicleTrainMaximumWeight; registration F.3 [11] |
| `axles` | integer | Number of axles of the motor vehicle | VehicleAxles; registration L [11] |
| `train_axles` | integer | Number of axles of the combination | — |
| `trailer_mass_kg` | integer | Technically permissible maximum laden mass of the towed vehicle, in kg; with two or more, their sum | registration F.1 of the towed vehicle [11] |
| `trailer_axles` | integer | Number of axles of the towed vehicle; with two or more, their sum | registration L of the towed vehicle [11] |
| `load_capacity_kg` | integer | Load capacity (payload) a carrier charges by, in kg: the technically permissible maximum laden mass less the mass in running order, of the semi-trailer for a tractor with semi-trailer, else of the motor vehicle and its trailers together | registration F.1 less G [11] |
| `load_kg` | number | Mass of the load the vehicle carries on the trip, in kg (the goods, without the vehicle) | consignment gross weight (e-CMR) |
| `length_m` | number | Overall length of the motor vehicle, in m | VehicleDimensions |
| `train_length_m` | number | Overall length of the combination, in m | — |
| `height_m` | number | Overall height, in m | VehicleDimensions |
| `first_axle_height_m` | number | Height of the vehicle measured over the first axle, in m | VehicleAxles.vehicleFirstAxleHeight |
| `width_m` | number | Overall width, in m | VehicleDimensions |
| `euro_class` | string | Euro emission class: `0`, `1`, `2`, `3`, `4`, `5`, `EEV`, `6`, `7` | EnvironmentalCharacteristics.euroValue |
| `co2_class` | integer | CO2 emission class 1 to 5 of Directive 1999/62/EC, Art. 7ga(2) | ISO 17573-3:2024 [5] |
| `energy` | string | `diesel`, `petrol`, `lpg`, `cng`, `lng`, `electric`, `hydrogen`, `hybrid`, `other` | EngineCharacteristics |
| `category` | string | UNECE vehicle category: `M1`, `M2`, `M3`, `N1`, `N2`, `N3`, `L` | registration J [11] |
| `trailer` | boolean | Whether the vehicle tows a trailer or semi-trailer | — |

**Derived values.** Where a usage does not give them, a calculator derives
these values, and no others, until none is left to derive: with `trailer`
`false`, `trailer_mass_kg` and `trailer_axles` are 0, `train_mass_kg` is
`mass_kg` and `train_axles` is `axles`; `trailer_axles` is `train_axles` −
`axles` when both are known; `trailer` is `true` if `trailer_axles` or
`trailer_mass_kg` is more than 0, and `false` if `trailer_axles` is 0. A
usage shall not give values that contradict these relations.

A law that charges each vehicle of a combination by its own mass or axles
(the motor vehicle and the trailer pay separately) is encoded as two charges:
one whose classes test `mass_kg` and `axles`, one whose classes test
`trailer_mass_kg` and `trailer_axles` (Annex D).

#### 6.6.2 Criteria

A criteria object maps parameters to conditions; parameters it does not name
are not tested.

- A numeric condition is an object with any of `min` and `max` (inclusive
  bounds) and `gt` and `lt` (exclusive bounds).
- A string condition is an array of the allowed values.
- A boolean condition is `true` or `false`.
- `any_of` is an array of two or more criteria objects, for a law that names
  alternatives ("Euro VI trucks, or electric or hydrogen ones").

An empty criteria object is met by every vehicle.

The criteria are decided with three values. A condition holds or fails by the
vehicle's value, and is undecided when the vehicle's description lacks the
parameter. `any_of` holds if one of its criteria is met, fails if all of them
fail, and is undecided otherwise. The criteria are met if every condition
holds, not met if any condition fails, and undecided otherwise. A calculator
shall not assume a missing value. 6.10.3 says how an undecided class affects
row selection; an undecided rule makes the statement incomplete (8.9).

#### 6.6.3 Class sets

`vehicle_class_sets` is a list of `{id, name, classes}`; `id` and `classes`
are required. Each class is `{id, label, criteria, fallback}`; `id` and
`criteria` are required. A vehicle is in the first class of each set, in list
order, whose criteria it meets, or in none; if an earlier class's criteria
are undecided, the vehicle's class in that set is undecided. `fallback`
names a class of the same set whose rows also apply to this class's
vehicles, ranked below the rows for this class (6.10.3). Fallbacks shall not
form a cycle.

A dataset may hold several sets, for example a closed system's own vehicle
groups beside the network's classes.

### 6.7 Time classes and calendars

A time class is `{id, label, days, times, defined, note}`; `id` is required.

`days` is a list of day selectors; a day is selected if any of them selects
it. Without `days` every day is selected. A day selector has these members,
all optional:

- `weekdays`: ISO weekday numbers, 1 for Monday to 7 for Sunday;
- `months`: month numbers, 1 to 12;
- `dates`: dates as `MM-DD` (every year) or `YYYY-MM-DD`;
- `date_ranges`: pairs `[from, to]` of dates, inclusive, both `MM-DD` (the
  range may wrap past the end of the year) or both `YYYY-MM-DD`;
- `easter`: pairs `[from, to]` of day offsets from Easter Sunday in the
  Gregorian calendar, inclusive;
- `calendars`: identifiers of calendars;
- `exclude`: a day selector, without `exclude`, of days removed.

A selector selects a day if its weekday is in `weekdays` (when given), its
month is in `months` (when given), it is one of the days of `dates`,
`date_ranges`, `easter` and `calendars` (when any of them is given), and
`exclude` does not select it. "Weekends in summer" is therefore one selector
(`weekdays` and `months`), and "summer or weekends" two.

A calendar is `{id, name, dates, covers_to}`; `id`, `dates` and `covers_to`
are required. `dates` lists `YYYY-MM-DD` dates, such as public holidays, and
`covers_to` is the last date for which the list is complete; no date in
`dates` shall be later than `covers_to`. Whether a calendar includes a date
after its `covers_to` is undecided. Day selection follows the three values
of 6.6.2: a selector is decided as soon as a decided part settles it, and a
time class is undecided for a day when no selector selects it and one is
undecided.

`times` is a list of local intervals `[start, end]` as `HH:MM`, `start`
inclusive and `end` exclusive; `start` shall not be `24:00`, and `end` may be.
An interval whose `end` is not after its `start` crosses midnight and belongs
to the day on which it starts. Without `times` the class covers whole days.
An instant is in the class if, read in the dataset's `timezone`, it falls in
an interval of a selected day. Instants carry their UTC offset (7.3), so an
instant is never ambiguous: in the hour that a change to daylight saving time
skips, no instant falls, and in the hour that a change back repeats, both
instants with that local time fall in an interval that contains it.

`defined: false` marks a time class the sources name but do not define, such
as a rush hour whose hours are not published. Whether an instant is in it is
undecided, and `coverage` shall list it.

### 6.8 User classes

A user class is `{id, label, payment, note}`; `id` is required. `payment`
lists payment means that make a user a member: `electronic` (on-board
equipment, or a contract with the toll charger or a toll service provider),
`account`, `card`, `cash`. A user holds a user class if the usage names it
(9.1) or uses one of its payment means.

### 6.9 Charge objects

| Member | Req. | Content |
| --- | --- | --- |
| `id` | yes | Identifier. |
| `type` | yes | `network`, `section`, `station`, `point`, `area` or `jurisdiction`. |
| `parents` | no | Objects that contain this one. Rows for an object apply to the objects below it (6.10.3). An object may have several parents when a network is divided on several dimensions at once: a km on a suburban motorway belongs to both "motorways" and "suburban roads". Parents shall not form a cycle. |
| `name`, `names`, `code` | no | Name; names by BCP 47 language tag; the operator's own code. |
| `operator`, `road` | no | Operator; road reference (`A4`, `E45`). |
| `network` | no | For a `network`: `{road_types, area, description}`; `road_types` from `motorway`, `trunk`, `other`; `area` is `suburban` or `interurban`. |
| `from`, `to` | no | For a `section`: its end places, each `{name, geometry, heading}` with `geometry` required. |
| `length_km` | no | For a `section`: its official length, in km. |
| `location` | no | `{geometry, openlr, osm, heading, match_m, headings, point_names}`: RFC 7946 geometry (7.4); an OpenLR reference, base64-encoded; OpenStreetMap element references; the paying direction in degrees clockwise from north (without it, both directions pay); the distance from the geometry, in metres, within which a passage is detected; for a `MultiPoint`, the paying direction and name of each point, in the order of the coordinates. |
| `jurisdiction` | no | For a `jurisdiction`: `{country, region}`, ISO 3166-1 alpha-2 country (required) and ISO 3166-2 subdivision. |
| `note` | no | Remarks. |

`location` and the end places state where and in which direction the toll
charger detects the use of the object: `geometry` is the detection place (a
gantry, barrier or cordon point as `Point` or `MultiPoint`, an area as
`Polygon` or `MultiPolygon`), `heading` the paying direction and `match_m`
the distance from the geometry within which a passage is detected. These
members are normative data; how a tool derives a usage's events from them is
map matching, which this document does not specify (clause 1). `osm` and
`network` are informative.

A station, point or area shall have a `location.geometry`, and a section a
`geometry` in both `from` and `to` or a `location.geometry`, unless no source
locates it; it shall then have none, and its `id` shall be a `scope` in
`coverage` (6.12). Networks and jurisdictions are described by their
attributes and need no geometry.

### 6.10 Charges

#### 6.10.1 Members

| Member | Req. | Content |
| --- | --- | --- |
| `id` | yes | Identifier. |
| `name` | no | Name. |
| `type` | yes | `distance`, `section`, `od`, `point`, `area`, `period` or `quantity` (6.10.2). |
| `component` | yes | What the charge pays for (see below). |
| `component_label` | no | The source's own name for the component. |
| `unit` | yes | What one amount is due for; one of the units its `type` allows (6.10.2). |
| `columns` | yes | Names of the row members, in order (6.10.3). |
| `rows` | yes | Arrays of values aligned with `columns`. |
| `objects` | see content | The charge objects the charge applies to; required when `columns` contains none of `object`, `entry` and `exit`. |
| `sources` | yes | Identifiers of the sources the amounts come from; at least one. |
| `basis` | yes | `official` (published as data by the toll charger), `transcribed` (copied from an official document), `derived` (computed from official figures) or `estimated`. |
| `unmatched` | no | `unpriced` (the default): a use no row matches is unpriced; `free`: it costs nothing. |
| `time_basis` | no | Which instant selects the time class: `entry`, `exit` or `event`; the default is `entry` for `od` and `event` otherwise. |
| `rounding` | no | `{increment, mode, stage}`, all required (8.7). |
| `volume` | see content | `{per, counts}`, both required when `columns` contains `volume` (6.10.3): the period the toll charger counts uses in, `day`, `month` or `year` (calendar periods, local time), and whose uses it counts, `vehicle` or `contract`. |
| `dynamic` | no | `{url, note}`: the charge's amounts are set in real time (ISO/TS 21192 [6]) and published at `url` (required); any rows are indicative. `coverage` shall list the charge as `unpriced`. |
| `tax` | no | Replaces the dataset's `tax` for this charge (6.4). |
| `valid_from`, `valid_to` | no | Local dates that narrow the dataset's validity for this charge; they shall lie within it. |
| `method` | no | The charging rule in words, where it differs from the dataset's. |

The components are:

- `infrastructure`, `air_pollution`, `noise`, `co2`, `congestion` and
  `markup`: the infrastructure charge, the external-cost charges for air
  pollution, noise and CO2 emissions, the congestion charge and the mark-up of
  Directive 1999/62/EC;
- `air_pollution_noise`: an external-cost charge for air pollution and noise
  together;
- `access`: a charge for entering or being in a zone;
- `carbon_price`: a price on the CO2 of fuel;
- `unspecified`: the sources do not split the charge into components;
- `other`: none of the above.

#### 6.10.2 Types

| `type` | Prices | `unit` | Type-specific members |
| --- | --- | --- | --- |
| `distance` | km driven on networks | `km`, or `tkm` (per tonne of mass and km) | `mass_basis` (the mass parameter: `mass_kg`, `train_mass_kg`, `trailer_mass_kg`, `load_capacity_kg` or `load_kg`; default `train_mass_kg`); `mass_cap_kg` (the mass above which `tkm` does not count); `mass_step_kg` (8.4) |
| `section` | each use of a section | `use`, or `km` (per km of the section's `length_km`) | — |
| `od` | each trip in a closed system, by entry and exit station | `trip`, or `t` (per tonne of mass per trip) | `directed` (default `false`: a row prices both directions of its pair); `mass_basis` for `t` (the mass parameter: `mass_kg`, `train_mass_kg`, `trailer_mass_kg`, `load_capacity_kg` or `load_kg`; default `train_mass_kg`); `mass_step_kg` for `t` (8.4) |
| `point` | each passage of a point | `passage`, or `t` (per tonne of mass per passage) | `mass_basis` and `mass_step_kg` for `t`, as for `od` |
| `area` | each day in a zone, or each entry into it | `day`, `entry` | — |
| `period` | each product bought | `product` | `day_basis` (`calendar`, the default, or `rolling`) |
| `quantity` | a quantity used in a jurisdiction | `t_co2`, `litre`, `kg` or `kwh` | — |

#### 6.10.3 Columns and rows

`columns` shall contain `amount` once and may contain each of these once:

| Column | Value |
| --- | --- |
| `object` | Charge object identifier; not for `od`. |
| `entry`, `exit` | Station identifiers; for `od` only, and both. |
| `vehicle_class` | Vehicle class identifier, from any set. |
| `time_class` | Time class identifier. |
| `user_class` | User class identifier. |
| `product` | ISO 8601 duration of the form `PnYnMnWnD` (`P1D`, `P10D`, `P1M`, `P1Y`); for `period` only, and required there. |
| `volume` | Integer from 1: the row applies from this use on in the period of the charge's `volume` (the first use is 1); for `section`, `od`, `point` and `area` only. |
| `priority` | Integer; `null` counts as 0. |
| `amount` | Decimal string (7.2), never `null`. |

The columns other than `amount` and `priority` are key columns. A key value
of `null` means "any". Two rows of a charge shall not have the same key and
`priority` values.

**Matching.** A row matches a use when each of its key values holds:

- `object`, `entry`, `exit`: the use's object, or an object above it through
  `parents`;
- `vehicle_class`: the vehicle's class in that class's set, or a class
  reached from it through `fallback`;
- `time_class`: a time class containing the instant that `time_basis` names
  (6.7);
- `user_class`: a user class the user holds (6.8);
- `product`: the product being priced;
- `volume`: a value no greater than the use's place in its period (8.4);
- `null`: anything.

**Ranking.** Each key value of a matching row has a rank: 0 for the use's
own value; *n* for an object *n* `parents` steps above the use's object (by
the shortest path) or a class *n* `fallback` steps from the vehicle's class;
for `volume`, the use's place minus the row's value; and last for `null`.
A row ranks above another if its `priority` is higher or, with equal
`priority`, if in the first key column, in the order of `columns`, where
their ranks differ, its rank is lower. The selected row is the matching row
that ranks above all others.

**Ties.** Rows that rank equally tie. If tied rows differ only in
`user_class`, the one with the lowest amount is selected (a user may hold
several user classes). Otherwise the use is unpriced (`ambiguous_rows`); a
producer shall not publish rows that can tie for any use, such as two rows
keyed by two parents of the same object at the same distance that differ in
nothing else.

**Undecided rows.** A row whose `vehicle_class`, `time_class` or `volume`
value is undecided for the use (6.6, 6.7, 8.4) can be counted neither as matching nor as
not matching. If such a row exists and no matching row ranks above it, the
use is unpriced: a calculator shall not select a row that an undecided row
might outrank.

### 6.11 Rules

A rule is `{id, kind, applies_to, params}`, all required; `applies_to` lists
the identifiers of the charges whose lines the rule acts on. Every kind's
`params` may have a `note`. In the table, members in italics are optional;
the others are required. The time and the local date of a line are those of
its event (8.4).

| `kind` | `params` | Effect |
| --- | --- | --- |
| `exemption` | `criteria` or `user_class` or both, *`from`*, *`until`* | When every condition given holds (the vehicle meets `criteria`; the user holds `user_class`, such as emergency services by contract), the lines dated from `from` to `until` (inclusive, when given) are removed. |
| `included_in` | `charge` (an `od` charge of the dataset), *`objects`* | A line on one of `objects` (any object, when not given) whose time lies between the entry and exit times, inclusive, of a trip priced by `charge` is removed. |
| `passage_group` | `objects`, `minutes`, `pays` (`first` or `highest`) | Only lines on the group's objects with an amount above zero count, in time order. A run starts at such a line; those less than `minutes` after its start belong to the run, and the run pays once: the first line's amount, or the highest. The other lines of the run become zero. The next line after the run starts a new run. |
| `factor` | `object`, `factor` | For a `km` or `tkm` line whose event attributes km to `object` (9.1, `overlays`), the amount of that share of the km is multiplied by `factor`. |
| `discount` | `name`, `percent`, *`criteria`*, *`user_class`*, *`payment`* | Applies when every condition given holds: the vehicle meets `criteria`, the user holds `user_class`, the usage uses one of the `payment` means. For each line, the percentages of the discounts that apply are added, at most 100, and the line's amount is reduced once by that percentage: 10 % and 20 % make 30 %. |
| `minimum` | `per` (`usage`), `amount` | If the rule's charges have lines in the usage and these total less than `amount`, an adjustment line adds the difference. |
| `cap` | `per` (`day`, `month` or `usage`), `amount`, *`time_class`* | If the lines of the rule's charges in a period total more than `amount`, an adjustment line subtracts the excess. With `time_class`, only the lines whose time is in the class count and are capped. |

`per: day` groups lines by local date, `month` by local month, and `usage`
takes all of them. An adjustment line (9.2) has as `charge` the first charge
of `applies_to` among the lines it adjusts.

### 6.12 Coverage (`coverage`)

A list of `{scope, status, reason}`; `scope` and `status` are required.
`scope` is `dataset` or the identifier of a charge object, vehicle class,
time class, user class, calendar, charge or rule; `status` is `complete`,
`partial` (part of what the scope covers is not priced, or not exactly) or
`unpriced` (none of it is priced); `reason` says what is missing. A dataset
with nothing missing shall state `[{"scope": "dataset", "status": "complete"}]`.

### 6.13 No charge (`no_charge`)

`{description, sources}` states that the area of the dataset's scheme
levies no charge of the kind the scheme names on the vehicles of
`liable_vehicles`: no road toll, user charge or vignette on a country's
roads, say. `description` (required) states it as the sources do, including
any charge it leaves out (a tunnel's or a bridge's, which other datasets
hold); `sources` (required) lists the identifiers of the sources (6.3) that
state it, which should be the law or the authority in charge.

A dataset with `no_charge` has no charge objects, charges or rules, and may
have no vehicle class sets; a dataset without it has at least one charge and
one vehicle class set. Its `coverage` is `complete` unless the statement
leaves part of the area or of the vehicles open, which `coverage` then says.
Without such a dataset, a calculation cannot tell an area that charges
nothing from one whose charges are not known.

## 7 Encoding

**7.1 JSON.** A dataset, a usage and a charge statement are each an I-JSON
text (RFC 7493) in UTF-8. Dataset file names should end in `.orct.json`.

**7.2 Decimals.** Every amount, rate, tax rate, percentage, factor and
rounding increment, and every quantity in a usage or statement, is a JSON
string matching `^-?[0-9]+(\.[0-9]+)?$`. Calculators shall use exact decimal arithmetic.
Measurements (masses, lengths, km in a usage) are JSON numbers; a calculator
shall read them as the exact decimal values they are written as.

**7.3 Dates and times.** Dates are `YYYY-MM-DD`; instants in a usage are
RFC 3339 date-times with an offset; times of day are `HH:MM`; durations are
ISO 8601-1 durations.

**7.4 Geometry.** An RFC 7946 geometry object of type `Point`,
`MultiPoint`, `LineString`, `MultiLineString`, `Polygon` or `MultiPolygon`,
with positions as `[longitude, latitude]` in WGS 84.

**7.5 Identifiers.** Case-sensitive strings, not empty, without leading or
trailing white space.

## 8 Calculation

**8.1 Inputs.** One or more datasets and one usage (9.1). Each event and
quantity names the dataset it belongs to; the steps below apply per dataset,
and the lines of all datasets form one statement.

**8.2 Applicability.** An event or quantity whose dataset is not given, or
whose object the dataset does not have, is not priced (`unknown_dataset`,
`unknown_object`). One whose local date lies outside the dataset's validity
is not priced (`outside_validity`). A charge prices only the events and
quantities whose local date lies within its own validity. A vehicle that does
not meet `liable_vehicles` owes nothing under the dataset; if that is
undecided, nothing is priced for the dataset (`missing_parameter`). A
dataset with `no_charge` (6.13) has no objects for events to name: it adds
no lines and no issues.

**8.3 Classification.** The vehicle's class is determined in every class set
(6.6.3), and the user classes the user holds (6.8).

**8.4 Uses.** An event is on a charge when its object, or an object above it
through `parents`, is in the charge's `objects` or in its rows' `object`,
`entry` or `exit` values. The uses of each charge type are:

- `distance`: each event on the charge is one use; its quantity is the
  event's `km`, or for `tkm` the `km` × min(mass, `mass_cap_kg`) / 1000, with
  the mass read from `mass_basis`. An event without `km` is unpriced
  (`missing_km`).
- `section`: each event on the charge is one use; for unit `km` the quantity
  is the section's `length_km`.
- `point`: each event on the charge is one use; for unit `t` its quantity is
  the mass read from `mass_basis` / 1000.
- `od`: the events on the charge, in time order, form trips: an event with
  role `entry` starts a trip, an event with role `exit` ends the trip, and
  other events continue the current trip or start one. Each trip is one use,
  from its first station to its last; a trip with one station (a barrier) is
  one use from that station to itself. Without `directed: true`, a row for
  the pair (B, A) matches the pair (A, B) when no row for (A, B) does. Where
  a toll charger ends one ticket and starts another (between concessions,
  for example), each closed system is its own charge, and a station where
  the systems meet is a station of both; a journey through several systems
  is then one trip in each.
  For unit `t` a trip's quantity is the mass read from `mass_basis` / 1000
  (a ferry's fare per tonne of load capacity, or of the load).

With `mass_step_kg`, the mass of a `tkm` or `t` charge counts in whole steps
of that many kg, a part of a step as a whole one, before `mass_cap_kg`: a
fare per started 1,000 kg of a load of 20,500 kg counts 21 t.
- `area`: for unit `day`, each local date with at least one event on the
  charge is one use, priced at the highest amount that any of that date's
  events selects; the date is unpriced if any of these selections is
  undecided. For unit `entry`, each event with role `entry` is one use.
- `period`: the local dates (`day_basis` `calendar`) or instants (`rolling`)
  of the events on the charge are covered by products. A product of duration
  D bought for date or instant s covers from s up to, not including, s + D,
  where months and years end on the same day of the month, or on the month's
  last day when it has no such day, and weeks are 7 days. A product's price
  is the row selected for it at its start (at 00:00 local time for
  `calendar`). Of the sets of products, each bought at a date or instant of
  use, that cover every date or instant of use, the one with the lowest total
  is chosen; among equal totals, the one with the fewest products; among
  those, the one whose row indexes, listed in date order, are first in
  lexicographic order. Each product bought is one use.
- `quantity`: each quantity of the usage whose object is on the charge and
  whose unit is the charge's unit is one use; its quantity is the `value`.

The time of a use, and of its line, is that of its event: for a trip, the
event `time_basis` names; for an `area` date, the event whose selection set
the amount; for a product, its start.

For a charge with a `volume` column, a use's place in its period is 1 plus
the number of the user's earlier uses of the charge in the same period: the
usage's uses before it, in time order, and, for the period of the usage's
first use, the uses the usage gives in `prior_uses` (9.1). If the usage gives
none for the charge, the place is undecided in that period.

**8.5 Amount of a use.** The row is selected as 6.10.3 specifies. A use that
no row matches is unpriced, or free if the charge's `unmatched` is `free`.
Otherwise the use's line has the row's amount as `rate`, and `rate` ×
quantity as `amount` (the quantity is 1 for the units `use`, `trip`,
`passage`, `day`, `entry` and `product`).

**8.6 Rules.** The rules of the dataset are applied to its lines in this
order of kinds: `exemption`, `included_in`, `passage_group`, `factor`,
`discount`, `minimum`, `cap`; rules of the same kind in the order of
`rules`.

**8.7 Rounding.** A charge's `rounding` rounds to a multiple of `increment`
(a decimal string) with `mode`:

- `half_up`: to the nearest multiple; halves away from zero;
- `half_even`: to the nearest multiple; halves to the even multiple;
- `up`: away from zero;
- `down`: toward zero.

With `stage: use`, each use's amount is rounded before the rules (8.5);
with `stage: line`, each line of the charge is rounded after the rules;
with `stage: charge`, the total of the charge's lines is rounded, and the
difference is an adjustment line. A charge without `rounding` keeps exact
amounts. The statement's total per currency is the sum of its lines, rounded
`half_up` to the minor unit of the currency (ISO 4217) and written with that
number of decimals.

**8.8 Tax.** Each line carries the tax basis and rate of its charge, or of
the dataset where the charge states none.

**8.9 Completeness.** The statement is complete (`complete: true`) when it
records no issue. Each of these is an issue, with the code given (9.2):

- an event or quantity names a dataset not given (`unknown_dataset`) or an
  object the dataset does not have (`unknown_object`), or lies outside the
  dataset's validity (`outside_validity`);
- the dataset requires a feature, or has a rule kind, the calculator does
  not implement (`unsupported_feature`, `unsupported_rule`);
- a vehicle parameter needed to decide `liable_vehicles`, a class or a
  rule's criteria is missing (`missing_parameter`);
- a distance event has no `km` (`missing_km`);
- a use's place in a volume period is undecided (`missing_count`);
- a use is of a charge with `dynamic` amounts (`dynamic_tariff`);
- a row that would be selected needs a time class that is not defined or a
  calendar past its `covers_to` (`unknown_time_class`);
- rows tie (`ambiguous_rows`);
- any other use is unpriced (`unpriced`);
- the usage touches a `coverage` scope whose status is not `complete`
  (`partial_coverage`): the dataset; an object an event or quantity is on, or
  an object above it; a charge with a use; a class the vehicle or user is in;
  a class a selected row names; or a rule that applies to a charge with a use.

The totals of an incomplete statement sum the lines that could be priced.

## 9 Usage and charge statement

**9.1 Usage.**

| Member | Req. | Content |
| --- | --- | --- |
| `orct_usage` | yes | Specification version, `"0.3"`. |
| `vehicle` | yes | The vehicle's parameters (6.6.1); parameters not known are left out. |
| `payment` | no | Payment means used (6.8). |
| `user_classes` | no | `{dataset id: [user class ids]}`: user classes the user holds by contract. |
| `prior_uses` | no | `{dataset id: {charge id: count}}`: for a charge priced by volume, the uses the toll charger has counted for this vehicle or contract earlier in the period of the usage's first use of the charge (8.4). |
| `events` | no | `[{dataset, object, time, role, km, overlays}]`, in any order; `dataset`, `object` and `time` are required. `role` is `entry`, `exit` or `pass`; `km` is the distance driven on a network; `overlays` is `{object id: km}`, the part of `km` driven on stretches inside the network that a `factor` rule names. |
| `quantities` | no | `[{dataset, object, unit, value, time}]`, all required: quantities used in a jurisdiction, such as tonnes of CO2 from fuel bought there. |

**9.2 Charge statement.**

| Member | Req. | Content |
| --- | --- | --- |
| `orct_statement` | yes | Specification version, `"0.3"`. |
| `complete` | yes | Boolean (8.9). |
| `lines` | yes | `[{dataset, dataset_version, charge, component, objects, row, quantity, unit, rate, amount, currency, tax_basis, tax_rate, basis, sources, notes}]`. `dataset_version` is the dataset's `version`, when it has one; `row` is the 0-based index of the selected row; `rate` its amount as written; `basis` the charge's `basis` (6.10.1), so that an estimated amount stays visible. An adjustment made by `minimum`, `cap` or rounding at `stage: charge` is a line of its own, with unit `rule`, no `row` or `rate`, and as `charge` the charge 6.11 names. `dataset`, `charge`, `component`, `objects`, `quantity`, `unit`, `amount`, `currency`, `tax_basis` and `basis` are required. |
| `totals` | yes | `[{currency, amount}]` (8.7). |
| `issues` | yes | `[{code, message, dataset, charge}]`; `code` and `message` are required. |

The issue codes are:

| Code | Meaning |
| --- | --- |
| `unknown_dataset` | An event or quantity names a dataset that was not given. |
| `unknown_object` | An event or quantity names an object the dataset does not have. |
| `outside_validity` | An event or quantity lies outside the dataset's validity. |
| `unsupported_feature` | The dataset requires a feature the calculator does not implement. |
| `unsupported_rule` | The dataset has a rule kind the calculator does not implement. |
| `unsupported_product` | A product's duration is one the calculator does not implement. |
| `missing_parameter` | A vehicle parameter needed by criteria or by a `tkm` or `t` charge is missing. |
| `missing_km` | A distance event has no `km`. |
| `missing_count` | A charge is priced by volume and the usage does not give its `prior_uses`. |
| `dynamic_tariff` | A use is of a charge whose amounts are set in real time. |
| `unknown_time_class` | A row that would be selected, or a cap, needs a time class that is not defined or a calendar past its `covers_to`. |
| `ambiguous_rows` | Rows tie (6.10.3). |
| `unpriced` | No row matches a use and `unmatched` is `unpriced`, or a use cannot be priced for another reason the message gives. |
| `partial_coverage` | The usage touches a coverage scope whose status is not `complete` (8.9). |

## 10 Versioning and extensions

**10.1 Versions.** `orct`, `orct_usage` and `orct_statement` hold the
specification version, `MAJOR.MINOR`. Until 1.0, any version may change
anything, without backward compatibility. From 1.0, a minor version only adds
optional members, and a major version may change meaning. Readers shall
ignore members they do not know, except as 10.3 says. A published dataset
should not change; a correction keeps its `id` and increases
`dataset.version`.

**10.2 Extensions.** `extensions` maps reverse domain names
(`org.example.tolls`) to objects; names without a dot, and names starting
with `x-` [18], are reserved. A dataset that keeps any part of its charging rules in an
extension shall list that part in `coverage` as `partial`.

**10.3 Features.** The feature identifiers are `type.distance`,
`type.section`, `type.od`, `type.point`, `type.area`, `type.period`,
`type.quantity`, `time_classes`, `calendars`, `user_classes`, `rounding`,
`volume`, `dynamic`, `rule.exemption`, `rule.included_in`,
`rule.passage_group`, `rule.factor`, `rule.discount`, `rule.minimum` and
`rule.cap`. A dataset shall list in `required_features` every feature it
uses: each charge type; `volume` when a charge has a `volume` column;
`dynamic` when a charge has `dynamic`; `time_classes` and
`user_classes` when a row or rule refers to one; `calendars` when a time
class refers to one; `rounding` when a charge has `rounding`; and each rule
kind.

## 11 Publication

A producer should publish its datasets with a feed: an `index.json` beside
them with these members.

| Member | Req. | Content |
| --- | --- | --- |
| `orct` | yes | Specification version. |
| `datasets` | yes | `[{id, scheme, country, name, file, sha256, valid_from, valid_to, coverage}]`: each dataset's identifier, scheme identifier, country, scheme name, path relative to the feed, SHA-256 of the file in hexadecimal, validity (`valid_to` `null` when open), and `complete` if every entry of its `coverage` is `complete`, otherwise `partial`. |
| `derived_from` | no | As in 6.2, for a feed converted from other data. |
| `jwks_uri` | no | URL of the producer's public keys, a JWK Set (RFC 7517). |

A producer should sign the feed: `index.jws` beside `index.json` holds a JWS
(RFC 7515) in compact serialization with a detached payload, the bytes of
`index.json`, signed with a key of the producer's `jwks_uri`. Since the index
lists each dataset's SHA-256, the signature covers every dataset. A
consumer can thus check that a dataset comes from the producer and has not
changed.

On EU national access points, feeds should be described with
mobilityDCAT-AP [16]. Sources should cite legal acts by ELI [17].

## Annex A (normative) Schemas

The JSON Schemas (draft 2020-12) of this document, identified by their `$id`:

- Dataset: `https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-0.3.schema.json` ([schema/orct-0.3.schema.json](../schema/orct-0.3.schema.json))
- Usage: `https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-usage-0.3.schema.json` ([schema/orct-usage-0.3.schema.json](../schema/orct-usage-0.3.schema.json))
- Charge statement: `https://raw.githubusercontent.com/majidkabir/orct/main/schema/orct-statement-0.3.schema.json` ([schema/orct-statement-0.3.schema.json](../schema/orct-statement-0.3.schema.json))

A schema cannot express every requirement of clauses 6 and 7, such as unique
identifiers, references and acyclic parents; the reference validator
([tools/validate.py](../tools/validate.py)) checks those too.

## Annex B (informative) Mapping to ISO 17575-3 and EN 16986

| ISO 17575-3 / EN 16986 element | ORCT |
| --- | --- |
| TollContextOverview / tollContextOverview (country code, provider identifier, name, version, validFrom) | `dataset` (`scheme`, `toll_charger.efc_provider`, `version`, `valid_from`) |
| TariffTable (tariffs, chargeUnit, roundingRule, version) | `charges` (`rows`, `unit`, `rounding`) and the dataset's `currency` |
| TariffClassDefinition (tariff classes, defined by tariff determinants such as vehicle parameters and time classes) | the key columns of a row |
| LocalVehicleClassDefinition | `vehicle_class_sets` |
| TimeClassDefinition | `time_classes` |
| UserClassDefinition | `user_classes` |
| TollContextLayout (charge objects and their geometry) | `charge_objects` |
| Charging principles: road section, area by distance, area by time, cordon | `section`; `distance`; `period` and `area` (unit `day`); `point` (cordon points) and `area` (unit `entry`) |
| ChargeReportingEvents, reporting rules | out of scope (map matching and reporting) |
| — (closed entry–exit systems, which are DSRC-based) | `od` |
| ISO 12855 toll declaration, billing details | usage (9.1), charge statement (9.2) |

## Annex C (informative) Mapping to other standards and laws

| Standard or law | Element | ORCT |
| --- | --- | --- |
| Directive 1999/62/EC | infrastructure, external-cost (air pollution, noise, CO2) and congestion charges; mark-up; user charge | `component`; `period` |
| Delegated Regulation (EU) 2020/203 [8], Annex I | publication of the correspondence between classification parameters and tariff classes | `vehicle_class_sets` |
| Implementing Regulation (EU) 2020/204 [9], Annex II | EETS domain statement | a dataset, as its machine-readable part |
| Delegated Regulation (EU) 2022/670 [10] | identification of tolled roads, applicable charges, payment methods | a dataset; `user_classes` |
| NeTEx Part 3 [12] | DistanceMatrixElement, UserProfile, TimeInterval, FareTable, Rounding | `od` rows, `vehicle_class` and `user_class`, `time_class`, rate table, `rounding` |
| GTFS Fares v2 [13] | rider categories, timeframes, rule_priority | user classes, time classes, `priority` |
| OCPI 2.2.1 [14] | TariffElement, PriceComponent, TariffRestrictions | row, amount, key columns |
| DATEX II [15] | OpenLR location references, validity | `location.openlr`, time classes |

## Annex D (informative) Examples

**D.1 A complete dataset.** A fictitious bridge toll: a price per crossing
by mass class, a night price, and 10 % off with an on-board unit.

<!-- example: dataset -->
```json
{
  "orct": "0.3",
  "dataset": {
    "id": "example.org/bridge/2026-01-01",
    "scheme": {"id": "bridge", "name": "Example bridge toll (fictitious)", "country": "DK"},
    "publisher": {"name": "Example toll charger", "role": "toll_charger", "url": "https://example.org"},
    "valid_from": "2026-01-01",
    "currency": "EUR",
    "timezone": "Europe/Copenhagen",
    "license": "CC0-1.0",
    "method": "A fixed price per crossing by mass class; night price from 22:00 to 06:00; 10 % off with an on-board unit.",
    "required_features": ["rounding", "rule.discount", "time_classes", "type.point", "user_classes"]
  },
  "sources": [{"id": "s1", "title": "Price list 2026", "url": "https://example.org/prices-2026.pdf"}],
  "tax": {"basis": "excluded", "rate": "0.25", "name": "VAT"},
  "liable_vehicles": {"description": "Vehicles over 3.5 t", "criteria": {"train_mass_kg": {"gt": 3500}}},
  "vehicle_class_sets": [{"id": "mass", "classes": [
    {"id": "up-to-12t", "criteria": {"train_mass_kg": {"max": 12000}}},
    {"id": "over-12t", "criteria": {"train_mass_kg": {"gt": 12000}}}
  ]}],
  "time_classes": [{"id": "night", "times": [["22:00", "06:00"]]}],
  "user_classes": [{"id": "obu", "label": "On-board unit", "payment": ["electronic"]}],
  "charge_objects": [{"id": "bridge", "type": "point", "name": "Example bridge",
                      "location": {"geometry": {"type": "Point", "coordinates": [11.0, 55.3]}}}],
  "charges": [{
    "id": "crossing", "type": "point", "component": "infrastructure", "unit": "passage",
    "basis": "transcribed", "sources": ["s1"], "objects": ["bridge"],
    "rounding": {"increment": "0.01", "mode": "half_up", "stage": "line"},
    "columns": ["vehicle_class", "time_class", "amount"],
    "rows": [["up-to-12t", null, "41.30"], ["up-to-12t", "night", "29.75"],
             ["over-12t", null, "65.50"], ["over-12t", "night", "47.20"]]
  }],
  "rules": [{"id": "obu-discount", "kind": "discount", "applies_to": ["crossing"],
             "params": {"name": "On-board unit", "percent": "10", "user_class": "obu"}}],
  "coverage": [{"scope": "dataset", "status": "complete"}]
}
```

**D.2 A usage.** A 40 t truck with an on-board unit crosses at 14:05 and at
23:40.

<!-- example: usage -->
```json
{
  "orct_usage": "0.3",
  "vehicle": {"train_mass_kg": 40000, "train_axles": 5, "euro_class": "6", "co2_class": 1},
  "payment": ["electronic"],
  "events": [
    {"dataset": "example.org/bridge/2026-01-01", "object": "bridge", "time": "2026-11-16T14:05:00+01:00"},
    {"dataset": "example.org/bridge/2026-01-01", "object": "bridge", "time": "2026-11-16T23:40:00+01:00"}
  ]
}
```

**D.3 The charge statement.** The day crossing selects row 2 (65.50) and the
night crossing row 3 (47.20), because `time_class` "night" ranks above
`null`; the discount takes 10 % off each.

<!-- example: statement -->
```json
{
  "orct_statement": "0.3",
  "complete": true,
  "lines": [
    {"dataset": "example.org/bridge/2026-01-01", "charge": "crossing", "component": "infrastructure",
     "objects": ["bridge"], "row": 2, "quantity": "1", "unit": "passage", "rate": "65.50", "amount": "58.95",
     "currency": "EUR", "tax_basis": "excluded", "tax_rate": "0.25", "basis": "transcribed", "sources": ["s1"],
     "notes": ["discount On-board unit 10%"]},
    {"dataset": "example.org/bridge/2026-01-01", "charge": "crossing", "component": "infrastructure",
     "objects": ["bridge"], "row": 3, "quantity": "1", "unit": "passage", "rate": "47.20", "amount": "42.48",
     "currency": "EUR", "tax_basis": "excluded", "tax_rate": "0.25", "basis": "transcribed", "sources": ["s1"],
     "notes": ["discount On-board unit 10%"]}
  ],
  "totals": [{"currency": "EUR", "amount": "101.43"}],
  "issues": []
}
```

**D.4 A closed system** with an electronic-payment price and a night price
that replaces both day prices. Without `priority` the electronic row would be
selected at night, because `user_class` comes before `time_class` in
`columns`.

<!-- example: charge -->
```json
{
  "id": "system-a", "type": "od", "component": "infrastructure", "unit": "trip",
  "basis": "transcribed", "sources": ["s2"],
  "columns": ["entry", "exit", "vehicle_class", "user_class", "time_class", "priority", "amount"],
  "rows": [
    ["a1", "a2", "heavy", null, null, 0, "9.40"],
    ["a1", "a2", "heavy", "electronic", null, 0, "8.93"],
    ["a1", "a2", "heavy", null, "night", 1, "4.70"]
  ]
}
```

**D.5 A barrier free at night** for every vehicle, overriding the class rows
through `priority`.

<!-- example: charge -->
```json
{
  "id": "barrier", "type": "point", "component": "infrastructure", "unit": "passage",
  "basis": "transcribed", "sources": ["s1"],
  "columns": ["object", "vehicle_class", "time_class", "priority", "amount"],
  "rows": [["gate", "c5", null, 0, "8.40"], ["gate", null, "night", 1, "0"]]
}
```

**D.6 Each vehicle of a combination.** A fictitious per-km fee that the
motor vehicle pays by its own permissible mass and the trailer by its own
(6.6.1). The class sets:

```json
[{"id": "motor", "classes": [
   {"id": "m18", "criteria": {"mass_kg": {"max": 18000}}},
   {"id": "m26", "criteria": {"mass_kg": {"gt": 18000}}}]},
 {"id": "towed", "classes": [
   {"id": "t10", "criteria": {"trailer_mass_kg": {"gt": 0, "max": 10000}}},
   {"id": "t24", "criteria": {"trailer_mass_kg": {"gt": 10000}}}]}]
```

and the two charges:

<!-- example: charge -->
```json
{
  "id": "motor-km", "type": "distance", "component": "unspecified", "unit": "km",
  "basis": "transcribed", "sources": ["s1"], "objects": ["all-roads"],
  "columns": ["vehicle_class", "amount"], "rows": [["m18", "0.12"], ["m26", "0.18"]]
}
```

<!-- example: charge -->
```json
{
  "id": "trailer-km", "type": "distance", "component": "unspecified", "unit": "km",
  "basis": "transcribed", "sources": ["s1"], "objects": ["all-roads"], "unmatched": "free",
  "columns": ["vehicle_class", "amount"], "rows": [["t10", "0.04"], ["t24", "0.09"]]
}
```

A tractor of 18 t with a semi-trailer of 24 t pays 0.12 + 0.09 per km. A
truck without a trailer (`trailer` `false`, so `trailer_mass_kg` is 0) is in
no `towed` class, and the trailer charge, `unmatched` `free`, costs it
nothing. A usage that gives `axles` and `train_axles` of a combination but
not `trailer_mass_kg` leaves the `towed` class undecided: the trailer charge
is unpriced (`missing_parameter`).

**D.7 Real datasets.** [data/carbon-cost/](../data/carbon-cost/) holds 238
datasets for 38 countries, converted from a third party's tables; each cites
its sources.

## Bibliography

1. ISO/IEC Directives, Part 2, *Principles and rules for the structure and drafting of ISO and IEC documents*
2. ISO 17575-3:2016, *Electronic fee collection — Application interface definition for autonomous systems — Part 3: Context data*
3. ISO 12855, *Electronic fee collection — Information exchange between service provision and toll charging*
4. EN 16986, *Electronic fee collection — Interoperable application profiles for information exchange between Service Provision and Toll Charging*
5. ISO 17573-3:2024, *Electronic fee collection — System architecture for vehicle related tolling — Part 3: Data dictionary*
6. ISO/TS 21192, *Electronic fee collection — Support for traffic management*
7. Directive (EU) 2019/520 of the European Parliament and of the Council on the interoperability of electronic road toll systems and facilitating cross-border exchange of information on the failure to pay road fees in the Union
8. Commission Delegated Regulation (EU) 2020/203 on classification of vehicles, obligations of European Electronic Toll Service users, requirements for interoperability constituents and minimum eligibility criteria for notified bodies
9. Commission Implementing Regulation (EU) 2020/204 on detailed obligations of European Electronic Toll Service providers, minimum content of the European Electronic Toll Service domain statement, electronic interfaces, requirements for interoperability constituents
10. Commission Delegated Regulation (EU) 2022/670 supplementing Directive 2010/40/EU with regard to the provision of EU-wide real-time traffic information services
11. Council Directive 1999/37/EC on the registration documents for vehicles
12. CEN/TS 16614-3, *Public transport — Network and Timetable Exchange (NeTEx) — Part 3: Public transport fares exchange format*
13. GTFS Schedule Reference, Fares v2
14. Open Charge Point Interface (OCPI) 2.2.1, Tariffs module
15. DATEX II, recommended reference profiles for Delegated Regulation (EU) 2022/670
16. NAPCORE, mobilityDCAT-AP 1.1.0
17. Council conclusions inviting the introduction of the European Legislation Identifier (ELI), 2012/C 325/02
18. IETF RFC 6648, *Deprecating the "X-" Prefix and Similar Constructs in Application Protocols*
19. ISO 17573-2:2025, *Electronic fee collection — System architecture for vehicle related tolling — Part 2: Vocabulary*

The survey of these sources, with links, is in [docs/research.md](../docs/research.md).
