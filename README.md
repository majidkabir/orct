# ORCT: Open Road Charge Tariff

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24395796.svg)](https://doi.org/10.5281/zenodo.24395796)

An open format for road charges (tolls, vignettes, zone and congestion
charges, external-cost charges and carbon prices on fuel), and a normative
method to compute the charges of one vehicle's trip from them.

**Status: 0.3, working draft for 1.0.** Until 1.0 anything may change, without backward compatibility.

## Why

No open standard publishes road charges together with the rule to compute
them. The ISO electronic fee collection standards (ISO 17575-3, ISO 12855)
model tariffs, but only for exchanges between toll chargers and their service
providers, sold and encoded in ASN.1. EU law asks national access points to
offer tolled roads and charges, but DATEX II has no tariff model for them.
Everyone who prices a trip rebuilds each scheme by hand.
[docs/research.md](docs/research.md) has the survey.

ORCT encodes the ISO 17575-3 concept model (charge objects; vehicle, time and
user classes; tariff tables; rounding) as open JSON. It extends that model to
what ISO 17575-3 leaves out (closed entry–exit systems, vignettes bought for a
period, carbon prices on fuel), and adds exact money, tax basis, provenance,
coverage and a calculation every implementation must agree on.
[docs/decisions.md](docs/decisions.md) gives the reasons for each choice.

## The model

A dataset holds one toll scheme for one validity period. Each charge is a rate
table: key columns (charge object, vehicle class, time class, user class,
product, volume) and an amount. The most specific matching row wins, unless a row's
`priority` says otherwise.

| Charge type | Prices | Example |
| --- | --- | --- |
| `distance` | km or tonne-km on a network | Germany's Lkw-Maut, Switzerland's LSVA |
| `section` | each use of a road section | Austria's special toll sections, Slovenia |
| `od` | a trip in a closed system, by entry and exit | French autoroutes, Sicily's A18 and A20 |
| `point` | each passage of a barrier, gantry, bridge or cordon point | Milan's ring roads, Norway's AutoPASS |
| `area` | each day in a zone, or each entry | London's Congestion Charge |
| `period` | a vignette product (`P1D`, `P7D` ...) | time-based user charges |
| `quantity` | tonnes of CO2 or litres of fuel | national CO2 taxes on fuel |

Rules cover exemptions, discounts, factors, passage groups, minimums and caps.
A dataset records whatever its sources leave out, for example unpublished
rush hours, unplaced stations or an unknown tax basis. A calculator then
reports an incomplete total instead of a wrong one.

## Contents

| Path | What |
| --- | --- |
| [spec/orct-0.3.md](spec/orct-0.3.md) | The specification |
| [schema/](schema/) | JSON Schemas for a dataset, a usage and a charge statement |
| [docs/research.md](docs/research.md) | Survey of existing standards and law |
| [docs/decisions.md](docs/decisions.md) | Design decisions and their reasons |
| [docs/review.md](docs/review.md) | Review questions, answers and open items |
| [data/carbon-cost/](data/carbon-cost/) | 238 datasets for 38 countries, as [carbon-cost](https://github.com/majidkabir/carbon-cost) keeps and prices them |
| [tools/validate.py](tools/validate.py) | Validates datasets: schema, references, row keys |
| [tools/orct_calc.py](tools/orct_calc.py) | Reference calculator |
| [tests/vectors/](tests/vectors/) | Conformance vectors: 46 covering every feature, 20 from official tariffs |
| [tests/record.py](tests/record.py) | Records the reference calculator's statements for sample usages of every charge, to compare another calculator with (the data workflow compares carbon-cost's) |
| [tests/smoke.py](tests/smoke.py) | Prices one use of every charge in every dataset |
| [tests/check_spec_examples.py](tests/check_spec_examples.py) | Checks the specification's Annex D examples against the schemas and the calculator |
| [tools/gen_schema.py](tools/gen_schema.py) | Generates the schemas |

## Use

```sh
pip install jsonschema
python3 tools/validate.py data/carbon-cost                       # check datasets
python3 tools/orct_calc.py usage.json data/carbon-cost/de/de-2024-07-01.orct.json   # price a trip
python3 tests/run_vectors.py                                     # conformance
```

A usage lists the charge objects a trip used, with times and km (spec 9.1);
finding them from a route (map matching) is out of scope, as in ISO 17575.

## Data

`data/carbon-cost/` is generated, not edited. The
[data workflow](.github/workflows/data.yml) converts carbon-cost's `main`
every day and on every change here. It validates the result, checks that no
price was lost, compares a sample of cases with carbon-cost's own engine, runs
the vectors and commits.
[data/carbon-cost/index.json](data/carbon-cost/index.json) lists every
dataset, its validity, coverage, and the carbon-cost commit it came from.

## Standardisation path

Open review here (issues and proposals), then a CEN Workshop Agreement, then
CEN/TC 278 WG1, where ISO 17575-3 is under review in 2026. A DATEX II mapping
would let national access points publish it under Reg. (EU) 2022/670.

## Licence

Specification text CC BY 4.0 ([LICENSE-SPEC.md](LICENSE-SPEC.md)), schemas and code [MIT](LICENSE). Each dataset
states its own licence; the carbon-cost data is MIT, from the public acts and
tariffs each dataset cites.
