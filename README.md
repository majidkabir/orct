# ORCT: Open Road Charge Tariff

An open format for road charges (tolls, vignettes, zone and congestion
charges, CO2 and carbon prices) and one rule for computing them for a truck's
trip. Draft 0.1.

No public standard does this today: the ISO tolling standards cover exchanges
between toll chargers and service providers, and EU law asks for toll data
without a format for it yet. See [docs/background.md](docs/background.md).

## Contents

| Path | What |
| --- | --- |
| [spec/orct-0.1.md](spec/orct-0.1.md) | The specification: dataset, the six charge types, modifiers, calculation, conformance |
| [schema/orct-0.1.schema.json](schema/orct-0.1.schema.json) | JSON Schema for a dataset |
| [data/carbon-cost/](data/carbon-cost/) | Every rate table of [carbon-cost](https://github.com/majidkabir/carbon-cost), converted, one folder per country |
| [tools/validate.py](tools/validate.py) | Checks files against the schema and their internal references |
| [tools/convert_carbon_cost.py](tools/convert_carbon_cost.py) | Converts carbon-cost's tables to ORCT |
| [tools/check_lossless.py](tools/check_lossless.py) | Checks the conversion kept every price |

## The model in one table

| Type | Prices | Example |
| --- | --- | --- |
| `distance` | km on a road class, operator or stretch | Germany's Lkw-Maut |
| `od_matrix` | an entry–exit pair of a closed system | French autoroutes |
| `point` | a passage of a barrier, bridge, tunnel or section | Norway's AutoPASS, Great Belt |
| `period` | a day or other period | Eurovignette countries |
| `zone` | a day in a zone | London's Congestion Charge |
| `quantity` | tonne-km or tonnes of CO2 | Switzerland's LSVA, fuel CO2 taxes |

Vehicle classes, time windows, payment medium, discounts, caps and tax apply
to all six. Whatever a source doesn't state is listed in `coverage`, so a
calculator reports an incomplete total instead of a wrong one.

## Data

`data/carbon-cost/<country>/<table>.orct.json`, with
[data/carbon-cost/index.json](data/carbon-cost/index.json) listing every
dataset, its validity and whether it is complete.

The folder is generated, not edited by hand. The
[data workflow](.github/workflows/data.yml) checks out carbon-cost's `main`
every day (and on every change here), converts, validates, checks nothing was
lost and commits the result. To run it yourself:

```sh
git clone https://github.com/majidkabir/carbon-cost ../carbon-cost
pip install jsonschema
python3 tools/convert_carbon_cost.py ../carbon-cost data/carbon-cost --commit "$(git -C ../carbon-cost rev-parse HEAD)"
python3 tools/validate.py data/carbon-cost
python3 tools/check_lossless.py ../carbon-cost data/carbon-cost
```

Every figure traces to its legal source through `sources`, and every file to
the carbon-cost table and commit it came from through `dataset.derived_from`.
`tax.included` is `null` throughout for now: carbon-cost records the tax basis
in each table's text (`dataset.method`), not as a field.

## Status and next steps

- 0.1 is a draft. Comments and proposals: open an issue.
- To come: test vectors (`tests/vectors/`) from operators' own worked
  examples, and a reference calculator that reads ORCT.

## License

[MIT](LICENSE). The data's sources are the public acts and tariffs each
dataset cites.
