# Survey of standards and sources

Survey date: 2026-11-15. Purpose: find what already exists for publishing road
charges and computing them for a trip, so ORCT reuses it instead of competing
with it. Each entry says what the source covers, what ORCT takes from it, and
what it leaves open.

## 1. Electronic fee collection (CEN/TC 278 WG1 and ISO/TC 204 WG5)

The two groups write EFC standards jointly
([itsstandards.eu](https://www.itsstandards.eu/its-application-areas/electronic-fee-collection/)).
All of them are sold, not open, and specify exchanges between toll chargers
(TC), toll service providers (TSP), on-board equipment and traffic managers,
not publication to the public.

| Standard | Covers | ORCT takes | Leaves open |
| --- | --- | --- | --- |
| [ISO 17575-3:2016](https://www.iso.org/standard/64163.html), context data | Back end → front end data for autonomous (GNSS) tolling: toll context overview, tariff information with tariff determinants (vehicle parameters, time classes), context layout, reporting rules; charging principles road section, area (distance or time) and cordon. ASN.1. | The concept model and terms: toll context, charge object, tariff classes defined by tariff determinants, vehicle, time and user classes, tariff table with charge unit and rounding rule, the three charging principles. | Closed (entry–exit) systems, which are DSRC-based; vignettes bought for a period; publication to the public; a normative calculation. Under systematic review in 2026 ([iss.rs](https://iss.rs/sr_Latn/project/show/iso:proj:64163), [genorma](https://genorma.com/en/standards/iso-17575-3-2016/amp)). |
| CEN ISO/TS 17575-3 data elements ([standardland.cz extract](https://www.standardland.cz/cen-iso-ts-17575-3/t850)) | TariffTable = tariffs, chargeUnit, roundingRule (optional), version and validity; PICS: TollRegimeOverview, TariffTable, TariffClassDefinition, LocalVehicleClassDefinition (mandatory), TimeClassDefinition, UserClassDefinition (optional), TollContextLayout, ChargeReportingEvents. | The same split into tariff table, class definitions and layout. | — |
| EN 16986:2024 profile of ISO 12855, as used by the Dutch HGV charge ([RDW TSP message description, June 2025](https://www.vrachtwagenheffing.nl/-/media/trucktol/website/documenten/info-voor-dienstaanbieders/hgv-charge--tsp--message-description-data-exchange-rdw--20250611.pdf), since removed from the site) | EfcContextData with tollContextOverview (country code, provider identifier, partitions, name, version, validFrom), tariffTable (Tariff, applicablePartitions, typeOfTariff, version), tariffClassDefinition (tariffClassId, description), localVehicleClassDefinition. | Shows the ISO structure in use: what the Dutch HGV charge sends its TSPs. ORCT's identifiers and versioning follow it. | Sent to contracted TSPs only. |
| [ISO 12855](https://www.iso.org/standard/88211.html) (2022, 2025; amendment DAM 1 in enquiry 2026, [DIN](https://www.din.de/en/wdc-beuth:din21:403836985)) | TC ↔ TSP back office: context data, toll declarations, billing details. The 2022 edition's Annex E gives an example toll calculation from tariff tables ([standardland.cz](https://www.standardland.cz/en/en-iso-12855/t2255)). | Toll declaration and billing detail as the model for ORCT's usage input and charge statement. | Bilateral; the calculation is informative only. |
| [ISO 17573-3:2024](https://ccn-scc.ca/standardsdb/standards/8188275) data dictionary | Common EFC data types: TariffClassId, TimeClassId, LocalVehicleClassId, VehicleClass, VehicleAxles, VehicleWeightLimits, EnvironmentalCharacteristics ([iteh sample](https://cdn.standards.iteh.ai/samples/85042/8073295072ae4772bf30339d61bcbd42/ISO-17573-3-2023.pdf)); the 2024 edition adds the CO2 emission class ([CEN WG1 convenor, May 2025](https://wpn.nen.nl/app/uploads/sites/14/2025/05/CO2-based-tolling-Eurovignette-Directive-and-EFC-standards.pdf)). | Vehicle parameter semantics. | — |
| ISO 14906 (EFC DSRC application interface) | Vehicle attributes: VehicleDimensions (length, height, width), VehicleWeightLimits (max laden weight, train maximum weight, unladen), VehicleAxles (first-axle height, axles, tyres), EuroValue, EngineCharacteristics (diesel, LPG, battery, hydrogen, ...) ([ASN.1 on ETSI forge](https://forge.etsi.org/rep/LIBS/LibIts/-/blame/6ea9334c7a9869ef643b71881da388897a206e02/asn1/IS/ISO_TS_14906_Application.asn?page=1), [Amd 1 sample](https://standards.iteh.ai/catalog/standards/iso/3d612e7c-918b-44f8-9e4e-a293ed7ce3b2/iso-14906-2011-amd-1-2015)). | ORCT's vehicle parameters are named after these attributes. | — |
| [ISO/TS 21192:2019](https://iteh.ai/catalog/standards/iso/37c75bf1-c1d8-4783-9ef7-d1894a074061/iso-ts-21192-2019) | TC ↔ road and traffic manager: level of service and tariff scheme messages. | Dynamic tariffs are a separate concern ORCT can point to. | — |

## 2. EU law

| Act | Says | Consequence for ORCT |
| --- | --- | --- |
| [Directive (EU) 2019/520](https://eur-lex.europa.eu/eli/dir/2019/520/oj) (EETS) and [Implementing Reg. 2020/204](https://eur-lex.europa.eu/eli/reg_impl/2020/204/oj) Annex II | Each toll charger publishes an EETS domain statement with minimum content. | Domain statements are documents; ORCT can be their machine-readable annex. |
| [Delegated Reg. 2020/203](https://eur-lex.europa.eu/eli/reg_del/2020/203/oj/eng) Annex I | A toll charger must publish the correspondence between vehicle classification parameters and its tariff classes at least three months before use. Parameters are those its roadside equipment can measure, or those in registration documents and standardised in clause 8.4 of EN ISO 14906:2018. | ORCT's vehicle parameters are drawn from those, so the publication the regulation requires can be an ORCT file. |
| [Directive 1999/62/EC](https://eur-lex.europa.eu/eli/dir/1999/62) as amended by [2022/362](https://eur-lex.europa.eu/eli/dir/2022/362/oj) | Defines toll (distance-based) and user charge (time-based); infrastructure, external-cost (air, noise, CO2) and congestion charges; mandatory CO2-class variation for heavy vehicles; a report on tolls every five years ([Trafikverket's report](https://trafikverket.se/contentassets/71b145a1697949378d31293a59d39046/rapport-om-infrastrukturavgifter-och-vagavgifter-eng.pdf)); CO2 class thresholds in a Commission note ([EC road charging](https://transport.ec.europa.eu/transport-modes/road/road-charging_en)). | ORCT's charge components use these definitions. |
| [Delegated Reg. (EU) 2022/670](https://eur-lex.europa.eu/eli/reg_del/2022/670/oj/eng) (RTTI) | National access points must offer identification of tolled roads, applicable fixed user charges and payment methods ([Council text](https://data.consilium.europa.eu/doc/document/ST-5967-2022-ADD-1/en/pdf)), in DATEX II or another format the Member States agree ([Art. 7](https://gesetze.legal/eu/vo_eu_2022_670/7)). | The legal hook for publishing ORCT on NAPs. |

## 3. DATEX II

The profiles for these RTTI data types say only "Information on this subject will be updated soon"
([tolled roads](https://docs.datex2.eu/recommended-profiles/rrp/rtti/rtti-670/3-rr-c-identification-of-tolled-roads/),
[variable charges](https://docs.datex2.eu/recommended-profiles/rrp/rtti/rtti-670/3-rr-d-variable-road-user-charges-and-available-payment-methods/)).
The v3.1 profile for variable road user charges states that DATEX II does not
support the category and recommends the EETS publications for tolling
([v3.1](https://docs.datex2.eu/v3.1/profiles/rrp/rtti/drd-11-variable-road-user-charges-and-payment-methods/index.html)).
DATEX II does support OpenLR location references
([DATEX II location](https://docs.datex2.eu/v3.3/location/5_OpenLR.html)).

**Gap confirmed:** the EU's own data format for these data types has no model for tariffs.

## 4. Tariff models in other domains

| Model | What it does well | What ORCT learns |
| --- | --- | --- |
| [NeTEx Part 3](https://normy.normoff.gov.sk/norma/142373/nahlad/) (CEN/TS 16614-3:2026), Transmodel | Very general fare model: fare structure elements, distance matrix elements (entry–exit prices), user profiles, time intervals, fare tables ([Entur's NeTEx profile](https://entur.atlassian.net/wiki/spaces/PUBLIC/pages/1638137934/fares)). NeTEx itself does not specify pricing algorithms ([CEN/TS 16614-3](https://shop.standards.ie/en-ie/standards/cen-ts-16614-3-2020-341675_saig_cen_cen_2830191)). Transmodel has a rounding step ([Transmodel 6.2](https://transmodel-cen.eu/model6.2/EARoot/EA6/EA2/EA1/EA3646.htm)). | Entry–exit matrices, class dimensions and rounding steps; ORCT adds the normative calculation NeTEx leaves out. |
| [GTFS Fares v2](https://gtfs.org/schedule/examples/fares-v2) | Small, open, community-governed; fare products, rider categories (adopted 2025, [GTFS digest](https://gtfs.org/blog/2025/03/06/gtfs-digest---february-2025---rider-categories-adopted/)), timeframes, explicit rule priority ([time-based fares](https://gtfs.org/documentation/schedule/examples/fares/time-based-fares/)). | Governance model, timeframes, deterministic rule matching. |
| [OCPI 2.2.1 tariffs](https://github.com/ocpi/ocpi/blob/2.2.1/mod_tariffs.asciidoc) (EV charging) | Tariff → elements → price components with restrictions (time, day of week, duration), with an open reference calculator ([ocpi-tariffs](https://docs.rs/crate/ocpi-tariffs/0.8.0)). The module deliberately sets no price-rounding rules, leaving them to law, contracts and currency ([module text, copy of the repository](https://vat.pages.dev/mikeatgravity/ocpi/blob/master/mod_tariffs.asciidoc)). | Restrictions as matching conditions; a reference implementation from day one; for published tolls, the rounding the source states has to be in the data. |
| [ISO/TS 5206-1:2023](https://standards.iteh.ai/catalog/standards/iso/de3896b8-9b6d-4761-afe3-ef7364d6da07/iso-ts-5206-1-2023) (parking, from APDS) | Rate tables and eligibility as an ISO data model. | An industry spec that became ISO: a route ORCT can follow. |
| [D-TRO](https://d-tro.dft.gov.uk/data-model-user-guide/release/v4.0.0/digital_traffic_regulation_orders.html) (UK DfT) | Open JSON model of traffic regulation orders, with rate tables and rate lines ([rateTable](https://d-tro.dft.gov.uk/data-model-user-guide/release/v4.0.0/Data%20Model%20HTML%20Guide/EARoot/EA2/EA113.htm)). | A national authority publishing legal charges as JSON. |
| [OpenEI Utility Rate Database](https://openei.org/services/doc/rest/util_rates) | Tiered rate structures referenced by 12 × 24 weekday and weekend schedules. | Separate the time schedule from the rate table. |
| [Open511 toll data](https://511.org/sites/default/files/pdfs/511%20SF%20Bay%20Open%20Data%20Specification%20-%20Toll%20Data_0.pdf) (SF Bay) | US toll programs with rates, tolled vehicle types, payment options, minimum and maximum toll. | A US regional precedent; this survey found no national US standard. |

US toll structures are at least as varied as Europe's: an analysis of 260 tollways found
one facility (LBJ Express, Dallas) with 4,836 distinct rates, and truck tolls around New
York set by axles, weight, vehicle type, height and other factors
([Coord](https://medium.com/coord/know-before-you-go-surprising-insights-from-analyzing-prices-of-260-tollways-29e83d150001)).

## 5. Commercial services

[HERE](https://docs.here.com/here-kb/docs/routing-api-returns-toll-prices-including-taxes-how-can-i-get-net-toll-costs-or-tax-breakdown-details)
returns tolls with taxes included and no breakdown;
[TollGuru](https://cms.ec2.mapup.ai/does-your-api-provide-toll-amounts-with-or-without-vat-for-europe/)
returns whether tax is included. Both are proprietary APIs, not open formats.

## 6. General building blocks

| Topic | Standard | Use in ORCT |
| --- | --- | --- |
| Numbers | [RFC 7493 (I-JSON)](https://www.rfc-editor.org/rfc/rfc7493) recommends strings for numbers needing exact interchange beyond double precision. | Money is a decimal string. |
| Extension names | [RFC 6648](https://www.rfc-editor.org/rfc/rfc6648) deprecates the "X-" convention. | Extensions are namespaced, not "x-" prefixed. |
| Location | GeoJSON (RFC 7946); [OpenLR](https://docs.ndw.nu/en/locatiereferentie/locatiereferentie-openlr/), map-agnostic and supported by DATEX II; [AGORA-C, ISO 17572-3](https://via-la.com/agora-c). | Coordinates required where known; OpenLR optional. |
| Time rules | OSM [opening_hours](https://wiki.openstreetmap.org/wiki/Key:opening_hours/specification) grammar, whose implementers call the specification messy ([opening-hours crate](https://docs.rs/crate/opening-hours/0.6.7/source/README.md)); GTFS timeframes; DATEX II validity. | A small structured time model, not a text grammar. |
| Legal references | [ELI](https://eur-lex.europa.eu/eli-register/eu_publications_office.html) URI templates. | Sources cite acts by ELI where one exists. |
| Catalogue metadata | [mobilityDCAT-AP 1.1.0](https://w3id.org/mobilitydcat-ap) (NAPCORE, CC BY 4.0). | How ORCT datasets are listed on NAPs. |

## 7. Conclusion

1. No open standard publishes road charges together with the rule to compute them.
   The ISO EFC model has the right concepts but is paid, encoded in ASN.1, and limited to
   contracted parties; DATEX II has no tariff model; fare and tariff standards in other
   domains exist and show it can be done.
2. ORCT should not invent concepts: it encodes the ISO 17575-3 concept model (charge
   objects; vehicle, time and user classes; tariff tables; rounding) in open JSON,
   extends it to what ISO 17575-3 leaves out (closed entry–exit systems, vignettes
   bought for a period, carbon prices on fuel), and adds what none of these standards
   specifies for published tariffs: a normative calculation, decimal money, tax basis,
   provenance and coverage.
3. The legal hooks to make it useful exist: Reg. 2020/203 (publish class
   correspondence), Reg. 2022/670 (NAP data types), Directive 1999/62 (charge
   components). The standardisation path is CEN/TC 278 WG1, whose base standard
   ISO 17575-3 is under review in 2026.
