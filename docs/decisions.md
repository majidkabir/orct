# Design decisions

Each decision below is hard to change once datasets exist. Each lists the
alternatives considered and why this one was chosen. Evidence is in
[research.md](research.md). Status: proposed for ORCT 0.2, the working draft
for 1.0.

## D1. Position: an open encoding of the ISO EFC tariff model, plus what it lacks

**Decision.** ORCT encodes the ISO 17575-3 concept model (toll context, charge
objects, vehicle/time/user classes, tariff tables, rounding) as open JSON and
adds four things no standard has: charging principles beyond autonomous tolling
(closed systems, vignettes, zones, carbon prices), a normative calculation,
exact money and tax basis, and provenance with coverage.

**Alternatives.** A new model from scratch (easier, but CEN/TC 278 WG1 would
see a competitor); a DATEX II extension (DATEX II has no tariff model and says
so); NeTEx Part 3 (public transport, no calculation).

**Why.** Reusing ISO concepts and terms makes ORCT reviewable by the EFC
experts who would have to accept it, and lets a toll charger generate ORCT from
the context data it already sends TSPs.

## D2. A rate table with key columns, not nested variants

**Decision.** A charge is a table: `columns` name the tariff determinants
(`object`, `entry`, `exit`, `vehicle_class`, `time_class`, `user_class`,
`product`, `priority`) plus `amount`; `rows` hold the values. This is ISO
17575-3's tariff class (a combination of determinants) and tariff table in
one structure, and NeTEx's fare table.

**Alternatives.** 0.1's per-class rate with named variants (night,
electronic): could not express a rate that varies by two determinants at once,
and every new variant needed a new name. Nested objects per object then class
then time: verbose for matrices with 10 000 pairs.

**Why.** One structure covers every charging principle, stays compact for
large matrices and maps one-to-one to CSV and to ISO tariff classes.

## D3. Row selection: most specific row wins, column order breaks ties, priority overrides

**Decision.** A row matches when each key equals the usage's value, an
ancestor of it (objects and vehicle classes have parents), or is empty
(any). Among matching rows: highest `priority` first; then compare column by
column in the table's column order, where exact beats ancestor, a near
ancestor beats a far one, and any value beats empty. Two rows with the same
keys are invalid.

**Alternatives.** Count of non-empty keys (ties between dimensions are
common and arbitrary); first row in file order (fragile under re-sorting);
explicit priority only (GTFS; forces publishers to number every row).

**Why.** Deterministic with no hidden order, and it expresses the common
patterns directly: an operator's own rate over the network default, a class
rate over a catch-all, a free-hours row over everything.

## D4. Vehicle classes are defined by standard vehicle parameters

**Decision.** Class criteria use a closed list of parameters named after
ISO 14906 / ISO 17573-3 attributes and registration data: `mass_kg`
(vehicle), `train_mass_kg` (combination), `axles`, `train_axles`,
`height_m`, `first_axle_height_m`, `length_m`, `train_length_m`,
`euro_class`, `co2_class`, `energy`, `category` (UNECE), `trailer`. A
dataset may hold several class sets (a closed system's own groups beside the
network's classes); a vehicle gets one class per set, the first it meets.

**Alternatives.** Each scheme's class labels only (not computable); free-form
parameters (not interoperable).

**Why.** Delegated Reg. (EU) 2020/203 Annex I limits toll classification to
these parameters and obliges toll chargers to publish how they map to tariff
classes. ORCT is that publication in machine-readable form.

## D5. Money is a decimal string

**Decision.** Every amount, rate, percentage and factor is a JSON string
holding a plain decimal (`"0.15607"`). Calculations use decimal arithmetic.

**Alternatives.** JSON numbers (OCPI does this; most parsers turn them into
binary floating point, and per-km rates times thousands of km drift by
cents).

**Why.** RFC 7493 recommends strings when exact interchange matters.
Invoices are reconciled to the cent.

## D6. Rounding and tax are explicit

**Decision.** Each charge may state `rounding` (increment, mode, stage). Each
dataset states `tax.basis`: `included`, `excluded`, `not_applicable` (a
public-law charge outside VAT) or `unknown`, with rate and name where known.
Statements carry the basis on every line.

**Why.** ISO 17575-3 has a rounding rule; OCPI leaves rounding open and its
implementers have to guess. HERE returns only gross tolls; sources often
don't state the basis. A standard must make the unknown visible.

## D7. Time: the dataset's time zone, structured time classes and explicit calendars

**Decision.** Every dataset names an IANA time zone. Time classes combine day
selectors (ISO weekdays, months, annual date ranges, dated ranges, Easter
offsets, calendars) with local time intervals; intervals may cross midnight.
Public holidays are explicit date lists (`calendars`). Each charge states
which instant counts (`time_basis`: entry, exit, passage).

**Alternatives.** The OSM opening_hours grammar (compact, but its own
implementers call the specification messy and holiday evaluation needs an
external database); iCalendar RRULE (powerful, hard to validate).

**Why.** Structured data validates with JSON Schema and evaluates the same
everywhere. A time class with no published definition is allowed but must be
marked `defined: false` and listed in coverage.

## D8. Charge types follow the charging principles

**Decision.** Seven types: `distance` (per km or tonne-km on a network),
`section` (per use of a road section), `od` (closed system, per entry–exit
pair), `point` (per passage of a barrier, gantry, bridge, tunnel or cordon
point), `area` (per day or entry in a zone), `period` (time-based user charge,
products such as `P1D`, `P10D`, `P1Y`), `quantity` (per tonne of CO2 or litre
of fuel).

**Why.** The first four plus `area` are ISO 17575-3's section, area and cordon
principles and the closed systems it leaves out; `period` is Directive
1999/62's user charge; `quantity` covers ETS2 and national CO2 taxes, which a
trip's cost needs too.

## D9. The calculation is normative, on a declared usage

**Decision.** The standard defines the usage input (the charge objects a trip
used, with times and km, as map matching outputs them), the algorithm, and the
charge statement output. Map matching stays out of scope, as in ISO 17575
where the front end detects charge objects.

**Why.** Two tools reading the same tariff must produce the same amount, or
the data isn't interoperable. Test vectors make that checkable.

## D10. Unknowns are data: coverage, `unmatched` and must-understand features

**Decision.** `coverage` lists what a dataset doesn't price. A charge says
what a usage with no matching row means (`unmatched`: `unpriced` by default,
or `free`). `required_features` lists the features a calculator must
implement; one that doesn't must mark its result incomplete, the way JOSE's
`crit` header works.

**Why.** A silent wrong total is worse than an incomplete one. This also lets
the format grow: new features can be added without old calculators
misreading them.

## D11. Locations: GeoJSON required where known, OpenLR and operator codes optional

**Decision.** Charge objects carry RFC 7946 geometry where it is known,
optionally an OpenLR reference (map-agnostic, used in DATEX II), OSM
references (informative only) and the operator's own code. An object a source
prices but nobody can place has no geometry and is listed in coverage.

**Why.** Coordinates work everywhere. OpenLR survives map differences. OSM ids
change, so they can't be normative.

## D12. Provenance per charge

**Decision.** Every charge cites sources (with ELI for legal acts where one
exists, retrieval date, file hash, page or table locator) and states its
`basis`: `official` (published as data by the toll charger), `transcribed`
(copied from an official document), `derived` (computed from official
figures) or `estimated`.

**Why.** Toll data is evidence in invoices and disputes; users must be able to
check every figure.

## D13. Extensions are namespaced; no "x-" prefix

**Decision.** `extensions` keys are reverse domain names
(`io.github.majidkabir.carboncost`). Unknown extensions are ignored; pricing
rules kept in one must be listed in coverage.

**Why.** RFC 6648 deprecates "x-" names because they leak into standards.

## D14. Versioning

**Decision.** `orct` holds the specification version. Minor versions only add
optional members; major versions may break. Until 1.0 the format may still
change. Datasets are immutable once published: a change is a new dataset with
a new `valid_from` or a new `version`.

## D15. Licences and governance

**Decision.** Specification text CC BY 4.0, schemas and tools MIT. Every
dataset states its own `license`. Governance follows GTFS: open issues,
proposals with at least one producer and one consumer, then a vote. Path to
formal standardisation: CEN Workshop Agreement, then CEN/TC 278 WG1 (where
ISO 17575-3 is under review in 2026), and a DATEX II mapping for national
access points, listed with mobilityDCAT-AP metadata.
