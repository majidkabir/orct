# Background: why ORCT

No standard describes how to publish road charges and compute them for a
truck's route. The nearest ones each cover one piece:

| Standard | Covers | Leaves out |
| --- | --- | --- |
| [ISO 17575-3:2016](https://www.iso.org/standard/64163.html) | Toll context and tariff data for GNSS on-board units | Paid; meant for the toll charger's back end, not published data |
| [ISO 12855:2025](https://www.iso.org/standard/88211.html) | Data between toll chargers and service providers | Bilateral and contract-bound |
| [Directive (EU) 2019/520](https://eur-lex.europa.eu/eli/dir/2019/520/oj), [Reg. 2020/204](https://eur-lex.europa.eu/eli/reg_impl/2020/204/oj), [Reg. 2020/203](https://eur-lex.europa.eu/eli/reg_del/2020/203/oj) (EETS) | Domain statements and the vehicle class to tariff mapping each toll charger publishes | Prose documents, no data format |
| [Directive 1999/62](https://eur-lex.europa.eu/eli/dir/1999/62) as amended by [2022/362](https://eur-lex.europa.eu/eli/dir/2022/362/oj) | Charge components (infrastructure, congestion, air, noise, CO2) and CO2 classes | Semantics only |
| [Reg. (EU) 2022/670](https://eur-lex.europa.eu/eli/reg_del/2022/670/oj/eng) and [DATEX II](https://docs.datex2.eu/recommended-profiles/rrp/rtti-670) | Tolled roads and charges as a national access point data type | The DATEX II [road user charging profile](https://docs.datex2.eu/recommended-profiles/rucp/) is still "TODO" |
| [ISO 14083:2023](https://www.iso.org/standard/78864.html) | Transport GHG emissions | No charges |
| [GTFS Fares v2](https://gtfs.org/schedule/examples/fares-v2) | Open public-transport fares | Transit only; the model to copy for shape and governance |

Gaps found while building [carbon-cost](https://github.com/majidkabir/carbon-cost)'s tables:

1. Operators publish PDFs, images, station matrices, calculators or prose.
2. Rounding, closed-system pairing and how barriers combine with distance
   rates are left to each consumer.
3. Every scheme has its own vehicle classes.
4. Many sources don't state whether VAT is included.
5. Stations in a tariff often can't be placed on a map.
6. Rates aren't tied to the act or sheet they come from.
7. Charges and emissions are separate worlds.

Every scheme found reduces to six charge types (per km, entry–exit pair, per
passage, per period, per zone day, per quantity) plus modifiers (class,
time, payment medium, discounts, caps, tax). That is what
[the spec](../spec/orct-0.1.md) defines.
