# Literature discovery, review, and extraction

## Current state

`data/raw/literature/source_register.csv` contains 11 source records:
eight metadata-verified citations, one indexed-abstract candidate, and
two full-text-inspected papers. The Bamboo PDF and the water-hyacinth PDF were
inspected; the registered *Ipomoea* thesis and composite leads remain
inaccessible. The existing thesis candidate has no verified DOI or
publication venue and is rejected for measurement extraction and model
pooling.

Access URLs and the review date (`2026-10-09`) are recorded per source in the
register. Publisher requests for the water-hyacinth article timed out, but its
CC BY 4.0 PDF was obtained from [Zenodo record 7746959](https://zenodo.org/records/7746959)
and retained under `data/raw/literature/full_text/`. For the NIT thesis,
repository page HTTP timed out, HTTPS and the repository search failed at the
transport layer, and the accessible NIT library page did not provide a copy.
OpenAlex reports no OA file; no public author email was found in the author's
ORCID record. Springer returned HTTP 406 for the inaccessible Ipomoea papers;
BPI publisher requests timed out. These checks describe access attempted here,
not proof that no lawful copy exists elsewhere.

The original six *Ipomoea* candidate sources still have no full-text
inspection in this project. The bamboo article's four-page PDF and the
water-hyacinth article's eight-page PDF were inspected on 2026-10-09. Both
remain pending/context-only because their fibre species are not *Ipomoea
carnea*. The water-hyacinth text rows and paper locators were checked against
its primary source; three text/Figure 6 conflicts remain unresolved. Bamboo's
nine graph values were visually rechecked but remain graph estimates.

The source-specific extraction files are kept separately under
`data/extractions/water_hyacinth/` and `data/extractions/bamboo/`. The original
root-level extraction files have been retained unchanged. These staged files
are outside the audit's raw-data roots; the normalized literature table below
is the single imported observation table, so the staged copies are not counted
as additional records.

`data/raw/literature/literature_observations.csv` now contains normalized
evidence rows from those bundles, with provenance links in `source_locator`
and `notes`. Water-hyacinth text values are verified as statements in that
paper, while the graph values remain estimates and the 0 wt% matrix-only
classification remains inferred. None of the 25 records is accepted or
model-eligible; no experimental measurements are present. Full-text
inspection does not make water hyacinth or bamboo compatible with the
intended *Ipomoea carnea* targets.

## Phase 9 source verification and discovery

- `BAMBOO-EPOXY-RAMARAO-2018`: the open four-page PDF from
  [Zenodo record 1163658](https://zenodo.org/records/1163658) was inspected.
  PDF p.1 gives the five-author byline; p.4 repeats the citation and DOI.
  The paper says it was published 10 January 2018, while Zenodo/DataCite give
  an issue date of 31 January; this date difference is retained.
  PDF p.2 Section 3 says 4/7/10 mm and 10/20/30 wt%, while Table 1/chart
  labels 6/8/12 mm and 15/30/45 wt%. This discrepancy remains unresolved.
  The PDF has no numeric tensile results table. The nine bars in the unnumbered
  p.3 Section 5.1 chart were re-read against its 2 MPa grid and agree with the
  existing estimates: 12/13/14, 14/15/16, and 16/18/19 MPa at 6/8/12 mm and
  15/30/45 wt%, respectively. All remain `graph_estimate`; no specimen-level
  data or replicate statistics are provided. Methods report epoxy plus HY
  951, 50 kg/24-hour mould compaction and 24-hour air cure, ASTM D3039-76,
  and a Tinius Olsen H10KS.
- `WH-EPOXY-SULARDJAKA-2023`: the eight-page CC BY 4.0 PDF from [Zenodo
  record 7746959](https://zenodo.org/records/7746959) was inspected; the
  publisher page/PDF timed out. PDF p.1 (journal p.26) gives the title,
  byline, DOI, and plant identity *Eichhornia crassipes*. PDF p.3 (journal
  p.28), Sections 4.2-4.3, reports mechanically extracted strands from
  50-70 cm stems, Bakelite EPR 174/V-140 epoxy, 5% and 10% NaOH or
  esterification for 24 h, 0/15/25/35 wt% loading, hand lay-up, a
  250 x 185 x 10 mm mould, 5 MPa compaction, water-jet cutting, ASTM D3039
  composites and ASTM D638 neat resin. Six specimens were tested per
  parameter; the paper does not identify means or report SD.
  PDF p.4 (journal p.29), Section 5.3, and p.6 (journal p.31), Conclusion 3,
  confirm the six existing numeric text rows: 41 MPa at 0 wt% (matrix-only
  interpretation still inferred), 45 MPa untreated at 25 wt%, 55 and 58 MPa
  at 15 and 25 wt% after 5% NaOH, and 59 and 61 MPa at 15 and 25 wt% after
  esterification. Figure 6 (PDF p.5/journal p.30) was inspected; its three
  35 wt% readings (~54, ~59, and ~42 MPa for untreated, 5% NaOH, and 10%
  NaOH) conflict with textual values 67, 51, and 35 MPa, respectively.
  These remain separate and unresolved. The abstract says 2/5/10% NaOH but
  methods list 5/10%; the esterification reagent is variously described as
  CH3COOH/acetic acid and acetate/acetic anhydride. No flexural, impact, or
  water-absorption result was found.
- New metadata-only *Ipomoea* leads are registered separately: the 1987 Chand
  and Rohatgi *Ipomoea carnea* particulate-polyester impact-toughness article
  (DOI 10.1007/BF01770929); two 2023 Preeti Nand Kumar book chapters on
  *Ipomoea carnea* pulp-blending strength (DOI
  10.9734/bpi/nacb/v4/6092e) and pulp/paper chemical components (DOI
  10.9734/bpi/nacb/v4/7079a). Crossref confirms these citations, but Springer
  and the BPI publisher pages were not accessible. They have no inspected
  target-property values and remain context-only, pending sources. Pulp/paper
  results are not polymer-composite evidence.
- Phase 3 follow-up literature investigation also identified:
  1. Raja et al. (2024), *Rice Bran Particulates Reinforced Ipomoea Carnea Fiber Epoxy Composite for Engineering Application*, Journal of Natural Fibers, DOI [10.1080/15440478.2024.2364253](https://doi.org/10.1080/15440478.2024.2364253). Publisher gateway returned HTTP 403 / anti-bot challenge on 2026-10-09; direct full-text automated extraction was blocked. Furthermore, the material system is a ternary hybrid composite (Ipomoea carnea + rice bran particulate + epoxy) which is conditionally comparable / distinct from binary non-hybrid composites.
  2. Palanisamy et al. (2026), *Mechanical, thermal, and environmental performance of Ipomoea carnea and Tecoma stans fiber-reinforced biophenolic hybrid composites*, Matéria (Rio de Janeiro), DOI [10.1590/1517-7076-RMAT-2023-0309](https://doi.org/10.1590/1517-7076-RMAT-2023-0309). It investigates hybrid biocomposites with Tecoma stans in a bio-phenolic matrix (BPR), not pure Ipomoea carnea in epoxy. Retained as context-only hybrid research.
- The existing 2013 NIT Rourkela thesis candidate remains abstract/index-only;
  its legacy repository page timed out, and the newer NIT handle with the same
  number points to an unrelated work. The 1986 composite article and 2014
  abrasive-wear epoxy article remain metadata-only. The 1988 DOI record is
  retained separately because its Crossref citation conflicts with Science
  Direct metadata pointing to the distinct 1987 Springer article; they have
  not been merged. The 2023 NaOH biomass-pretreatment paper remains biomass
  processing evidence, not composite mechanical-property evidence.

Across the imported table, evidence labels remain 9 numeric
text-reported-value records, 16 graph-estimate records, 0 numeric inferred
records, and 3 unresolved numeric text/figure conflict pairs. Six existing
water-hyacinth text rows are now confirmed against the primary paper; the
three text/figure conflicts are retained. The fourth water-hyacinth comparison
is a graph estimate with a non-numeric, text-derived comparison. All remain
ineligible for training.

## Source register fields

The source register is a bibliographic/review table, not a measurement file.
It records a stable `source_id`, title, authors, year, journal, DOI/URL,
metadata provider, inspected access level, access URL and ISO access date, an
extraction-confidence statement, known fibre/matrix/treatment/testing details,
compatibility category, verification status, review status, and review notes.
Unknown information is blank.

Allowed review statuses are `pending`, `accepted`, and `rejected`. Allowed
compatibility categories are `directly comparable`, `conditionally
comparable`, `context only`, and `rejected`. A source enters literature model
training only when a reviewer has explicitly set it to `accepted` and
`directly comparable`; the existing one-source-at-a-time model requirements
still apply. Conditional sources need target-specific documented restrictions
and are not automatically eligible.

The included source records are screening candidates, not an assertion that
their studies are compatible:

- `LIT-IC-1986` has Crossref-verified citation metadata, but fibre forms,
  matrices, test protocols and target data remain unreviewed because the paper
  was inaccessible. The DOI route redirected without article content, the
  direct ScienceDirect PII route led to an unrelated silver-nanoparticle
  article, and Unpaywall listed no repository copy. It is context only.
- `LIT-IC-1988` has DOI/title/year/journal metadata; author names were not
  present in the inspected registry response. Its title identifies
  particulate *Ipomoea carnea* in polyester, not epoxy fibre reinforcement.
  Its Crossref citation says *Composites* 19(1), p.79 (1988), but the
  ScienceDirect record labels the item a “Literature alert” and embeds a
  citation to the distinct 1987 Chand-Rohatgi Springer paper. The 1988 DOI
  record is not evidence of an independent experiment; the DOI records remain
  separate, with the 1988 alert record rejected for measurement extraction
  and retained only for DOI disambiguation.
- `LIT-IC-1987-IMPACT` is a separate Crossref/OpenAlex-verified citation by
  Navin Chand and P. K. Rohatgi, *Journal of Materials Science Letters*,
  6(6), 695-697 (1987), DOI 10.1007/BF01770929. The Springer page returned
  HTTP 406 and Unpaywall reported no open-access or repository copy; no result
  values or methods were inspected. Its title indicates particulate-polyester
  impact toughness, not fibre-reinforced epoxy.
- `LIT-IC-2014` has citation metadata verified through Crossref/Unpaywall.
  Springer returned HTTP 406; OpenAlex and Unpaywall reported closed access and
  no repository copy. The title concerns abrasive wear, outside current
  target properties.
- `LIT-KENAF-2012` concerns treated/untreated kenaf/epoxy flexural behavior.
  Crossref/Unpaywall citation metadata were verified, but article/test details
  were unavailable. Different fibre species and unverified test conditions
  prevent pooling with the intended Ipomoea carnea system.
- `LIT-IC-2013-CANDIDATE` has an OpenAlex-indexed abstract, not a verified
  publisher record. The indexed dissertation title is *Investigation into
  Mechanical and Tribological Properties of Ipomoea carnea Reinforced Epoxy
  Composite* (Kamal Kumar Basumatary, 2013); the NIT Rourkela item is 5168.
  The abstract describes epoxy composites with particulate concentrations,
  but gives no test names or numerical results. Both HTTP and HTTPS repository
  routes were inaccessible; OpenAlex lists closed access and no PDF. Venue,
  full text, methods and results remain unverified. The next legitimate route
  is a repository/library request or a copy from the author. It remains
  rejected for extraction and model pooling.
- `LIT-IC-NAOH-2023` has Crossref-verified metadata for a paper on NaOH
  pretreatment of Ipomoea biomass for clean-energy processing. It is not a
  fibre-reinforced polymer study; AIP full text could not be accessed and no
  treatment concentration or composite measurement was extracted. It is
  context only.
- `LIT-IC-PULP-2023` and `LIT-IC-CHEM-2023` are Crossref-verified 2023 book
  chapters by Preeti Nand Kumar, respectively about *Ipomoea carnea* pulp
  blending/strength (pp. 25-33; DOI 10.9734/bpi/nacb/v4/6092e) and pulp/paper
  chemical components (pp. 172-182; DOI 10.9734/bpi/nacb/v4/7079a). The
  publisher pages timed out; only titles and citation metadata were checked.
  They are pulp/paper context, not polymer-composite measurements.
- `WH-EPOXY-SULARDJAKA-2023` now has Crossref/OpenAlex-verified bibliographic
  metadata and full-text inspection. Its publisher page and PDF requests
  failed, but the CC BY 4.0 PDF was obtained from Zenodo record 7746959 and
  retained locally. The primary text confirms six numeric text rows; Figure 6
  conflicts with three textual 35 wt% values. See the verification findings
  above and `data/extractions/water_hyacinth/EXTRACTION_NOTES.md`.
- `BAMBOO-EPOXY-RAMARAO-2018` is full-text inspected via its four-page
  Zenodo PDF. Its nine chart readings remain graph estimates and the paper
  concerns bamboo, so it is context only and is not eligible for modelling.

No lawful full text was located for the registered *Ipomoea carnea* thesis,
1986/1987/1988 composite leads, or 2014 abrasive-wear paper in this follow-up.
The thesis repository item and search endpoints were inaccessible; NIT's
library landing page did not provide a copy, and OpenAlex lists closed access
with no PDF. The public ORCID record did not expose a public email. The thesis
abstract and bibliographic records are not experimental evidence. No
observation values were added or changed. The water-hyacinth source status and
observation locators/notes were updated after full-text inspection; the
25-record count and all model-eligibility decisions remain unchanged.

For the original six sources, five have DOI-backed bibliographic metadata and
the 2013 candidate has index metadata plus indexed abstract text. The two extraction-bundle citations are separately registered and both are
full-text-inspected. Author names are left blank where the bibliographic
record did not provide them. DOI/index records verify discovery metadata, not
experimental methods, numerical results, or scientific claims.

## Supplied extraction-bundle integration

The repository contained two identifiable paper extractions, not three
identifiable literature sources:

- `WH-EPOXY-SULARDJAKA-2023` is based on
  `data/wh_epoxy_tensile_extraction.xlsx`. The workbook gives a citation,
  locators, five fibre-composite text values, a 0 wt% matrix-baseline value,
  four graph readings, and four text/figure comparison entries. The baseline
  is numerically transcribed as reported but its matrix-only interpretation is
  explicitly identified by the bundle as inferred. The fourth comparison's
  text side is derived from a percentage statement and has no exact numeric
  value; it is not turned into a fabricated point. Its figure reading is the
  same estimate as WHE04 and was not duplicated. The six text rows and
  locators were subsequently checked against the primary paper; the three
  35 wt% text/Figure 6 conflicts remain unresolved.
- `BAMBOO-EPOXY-RAMARAO-2018` is based on `data/source_record.json`,
  `data/EXTRACTION_NOTES.md`, and `data/estimates_graph.csv`. The bundle says
  it contains no directly reported numeric tensile result and nine chart
  estimates. Its prose and table/chart disagree on fibre lengths and loadings;
  chart labels are retained only as the conditions attached to those graph
  readings, with the conflicting prose recorded in the notes.

The source-specific staged files are separated under
`data/extractions/water_hyacinth/` and `data/extractions/bamboo/`; source
specific copies do not create additional literature-review inputs. The
supplied workbook and extraction CSVs are retained unchanged. The normalized
rows preserve their supplied record IDs and workbook locators, now alongside
primary-paper page/figure locators for the water-hyacinth checks and the
bamboo chart review.

| Bundle column/field | Canonical field | Handling |
|---|---|---|
| `obs_id`, `Est. ID` | `record_id` | Namespaced by stable source ID; text/figure sides of conflicts have separate IDs. |
| `source_id` | `source_id` | Preserved; citation fields copied from the supplied metadata only. |
| `fibre_species` | `fibre_type` | Species uncertainty retained verbatim; water hyacinth and bamboo remain distinct. |
| `matrix` | `matrix_type` | Resin/hardener wording preserved; unreported ratios remain unfilled. |
| `treatment_type`, `treatment_conc`, duration | `treatment_method`, `naoh_concentration_pct`, `treatment_time_h` | Only explicitly supported conditions populated; unknown conditions stay blank. |
| `fibre_loading`, `fibre_length_mm`, `fibre_form`, `process` | matching canonical fields | Chart-labelled bamboo conditions are accompanied by the unresolved prose conflict. |
| `property`, `value`, `unit` | `test_type`, `measured_value`, `measured_unit` | Only supported tensile-strength values are represented; source text is not converted into other targets. |
| `test_method` | `test_standard` | Recorded standard retained; equipment/method details remain in `notes` when no canonical field exists. |
| `value_basis` | `extraction_type` | `reported_value` preserves numeric text values with unspecified statistic; `graph_estimate` stays visibly estimated. |
| `text_location`, `figure_location` | `source_locator` | Original locators plus bundle worksheet/row identifiers and primary-paper PDF/journal page locators where checked. |
| `statistic`, `reading_uncertainty`, `crosscheck`, `notes` | `notes` | Preserved as caveats; no specimen, mean, or uncertainty is inferred. |

The canonical review extension recognizes `individual`, `reported_mean`,
`reported_range`, `reported_value`, `graph_estimate`, and `inferred`.
`reported_value` means the source/bundle gives a numeric value but does not
identify its statistic; it is not treated as an individual specimen result or
mean. `graph_estimate`, `inferred`, and `reported_value` are evidence-only and
are explicitly excluded from model training. Graph readings remain separate
from text values; unresolved text/figure pairs remain pending. The supplied
matrix-baseline number is retained but rejected as a fibre-composite row.

The integrated table has 25 records: nine `reported_value` rows and sixteen
`graph_estimate` rows. These include five unconflicted water-hyacinth
fibre-composite text values, one water-hyacinth matrix baseline, three
additional text values paired with three estimates for unresolved 35 wt%
conflicts, four water-hyacinth graph readings, and nine bamboo graph readings.
There are three unresolved numeric text/figure conflict pairs; a fourth
bundle conflict remains in the original file because its text value is only
derived/approximate and its figure estimate duplicates WHE04. No numeric
`inferred` point was created. All 25 records are pending or rejected and
context-only. The water-hyacinth text values are verified against the article;
its figure readings and bamboo readings were rechecked but remain estimates.
All evidence remains ineligible because the sources are pending/context-only,
and the fibres do not match the intended *Ipomoea carnea* system. The exact
source/batch and material compatibility requirements remain unchanged.

The large `data/Raw Data/` folder is a separate collection of 558 instrument
CSV exports labelled by carbon/flax/jute material groups. It has no matching
literature citation or canonical observation schema in the supplied material;
the files were not imported as literature or experimental observations.

## Review and extraction workflow

1. Find a paper through a publisher, institutional repository, or index.
2. Confirm title, author list, year, journal, and DOI against publisher and/or
   DOI-registry metadata. Record access URL/date and exactly which content
   level was inspected: metadata, abstract, or full text. An indexed abstract
   must be labelled as such; do not imply the publisher page was inspected.
3. Review the paper itself before transcribing experimental conditions.
   Capture the section/page/table/figure for each value; do not fill unknown
   values from secondary sources or assumptions.
4. Assign a compatibility category and review status with a written reason.
   Keep epoxy, polyester, different fibre species/forms, treatment processes,
   test standards, and property definitions distinct unless scientific review
   justifies a restricted comparison.
5. Add only source-traceable observations to
   `literature_observations.csv`, one reported value per row. Preserve
   reported averages/ranges as reported summaries—not fabricated specimen
   rows. `extraction_type` distinguishes `individual`, `reported_mean`,
   `reported_range`, `reported_value` (statistic unspecified), `graph_estimate`,
   and `inferred`; evidence types other than the first three are not model
   inputs. Record the supporting location in `source_locator`.
6. Re-run literature review and structural validation. Raw input files are
   never rewritten by the review/report commands. Edit/replace curated source
   files deliberately with version control and preserved copies.

No automatic scraping, downloading, or extraction is performed. Do not
download copyrighted full texts from unauthorized sources. Graph-digitized
values require a documented digitization procedure and uncertainty and must
not be represented as exact measured specimen values.

## Commands

Run the non-destructive register/extraction review:

```powershell
python -m ecofiber_ai literature review
```

Write the report somewhere other than the default processed directory:

```powershell
python -m ecofiber_ai literature review --output-dir data/processed/literature-review
```

Validate the extracted observation table with the canonical validator:

```powershell
python -m ecofiber_ai validate data/raw/literature/literature_observations.csv
```

This creates a processed validation copy/report. The source register is not an
observation CSV and is validated by `literature review`, not by the canonical
measurement validator.

## Modelling and data gaps

The review report separately lists source counts and observation counts per
target, including provenance-complete and directly-comparable accepted rows.
The baseline model refuses literature rows unless their `source_id` is
explicitly `accepted` and `directly comparable` in the register. It does not
pool sources automatically.

No target currently has accepted, verified, directly comparable observations.
The 25 imported bundle entries remain pending/context-only evidence and do not
satisfy readiness. Water-hyacinth text values are source-checked, but that
different fibre species is not accepted for the project targets; graph
estimates, inferred classification, and unresolved conflicts remain
ineligible. At minimum, each candidate model needs source-verified target
values and units, fibre and matrix identity,
treatment/loading/fabrication and testing details sufficient for compatibility
review, study/batch identifiers, and enough independent groups to meet the
existing model thresholds. Literature citation metadata alone does not satisfy
these requirements.
