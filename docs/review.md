# Review questions and status

Questions a reviewer from CEN/TC 278 WG1 (electronic fee collection) would
ask, with the answer and what was done. "Open" items need people or decisions
outside this repository.

| # | Question | Answer | Status |
| --- | --- | --- | --- |
| 1 | Why a parallel model rather than a JSON encoding (ASN.1 JER) of ISO 17575-3 context data, or a new part of ISO 17575? | A JSON encoding would keep ISO 17575-3's scope: no closed systems, no vignettes, no normative calculation, coverage or tax basis. ORCT maps to ISO 17575-3 element by element (Annex B), so it can also become a new part of ISO 17575. | Open: WG1 to decide the vehicle. |
| 2 | If a toll charger publishes ORCT and EN 16986 context data, which is authoritative? | The context data, for billing. A dataset now names the context data it was generated from (`dataset.efc_context`). | Done (spec 6.2). |
| 3 | Why not the terms of ISO 17573-2? | They should be. The spec now cites ISO 17573-2 and lets it prevail; "charge object" uses its wording. The other definitions need the text, which is not freely available. | Partly done; open: alignment of every term. |
| 4 | Carbon prices on fuel are not road charges; why in an EFC standard? | For trip costing. It is a separate charge type (`quantity`) and feature, so it can be moved out of the EFC deliverable. | Open: WG1 to decide. |
| 5 | Has a national access point or Member State agreed to it under Reg. (EU) 2022/670? A DATEX II mapping? | No. | Open. |
| 6 | Trailers and the CO2 class of combinations (pending amendment of Directive 1999/62/EC)? | Combination mass, axles and a trailer flag exist; a parameter for the combination's CO2 class waits for the final text. | Open: law not final. |
| 7 | Exemptions by owner or purpose (emergency services, military)? | An exemption can now be by user class, held by contract. | Done (spec 6.11; vector exemption-user-class). |
| 8 | Volume and annual discounts (Øresund's 500 crossings a year)? | Rows can be keyed on `volume`, the use's place in its day, month or year; the usage gives earlier uses (`prior_uses`). | Done (spec 6.10.3, 8.4; vectors point-volume, point-volume-unknown). |
| 9 | Legal source for splitting chained closed-system trips? | None existed; the rule is removed. Each closed system is its own charge, sharing the station where they meet. | Done (spec 8.4, decision D16; vectors od-two-systems, od-barrier). |
| 10 | Rounding before discounts, or per section? | Per section was already possible (one use per section). Rounding per use before the rules is now a stage. | Done (spec 8.7; vector rounding-per-use). |
| 11 | Several currencies, VAT per component, VAT changes during validity? | One currency per dataset; tax per charge; a rate change is a new charge with its own validity. | Answered. |
| 12 | Local times that occur twice or not at all (daylight saving)? | Instants carry their offset; the spec now says how both cases fall. | Done (spec 6.7). |
| 13 | Tariffs set in real time (ISO/TS 21192)? | A charge can be declared `dynamic`, with the URL of its live tariff; its uses are reported, not priced. | Done (spec 6.10.1; vector dynamic-tariff). |
| 14 | Map matching decides the result; how do two parties agree? | Conformance covers usage to statement. A route-to-usage conformance level is possible later. | Open. |
| 15 | Is informative location data enough to publish where vehicles are detected? | Detection place, paying direction and detection distance are now normative data; map matching stays out of scope. | Done (spec 6.9). |
| 16 | Liability for estimated amounts? | The publisher is named in every dataset; statement lines now carry `basis`, so an estimate stays visible. | Done (spec 9.2). |
| 17 | How is a dataset's origin verified? | The feed lists each file's SHA-256 and is signed with a detached JWS. The carbon-cost feed has the hashes; signing needs the producer's key. | Done in the spec (clause 11) and the hashes; signing open. |
| 18 | Reconciling invoices across corrected datasets? | Lines carry `dataset_version`. | Done (spec 9.2). |
| 19 | Official test vectors and certification? | 20 vectors now use official published amounts (Austria, Denmark, Germany, Milan, Sicily), 38 are synthetic. Official vectors from toll chargers, and certification, need them. | Partly done; open. |
| 20 | Which deliverable, which sponsor, and the licences against CEN copyright? | Proposed path: CEN Workshop Agreement, then a Technical Specification in TC 278 WG1. No sponsor yet; the licences need CEN-CENELEC's IPR policy. | Open. |
| 21 | Who has implemented or reviewed it? | No toll charger or service provider yet; there is one converter and one reference calculator. | Open. |
