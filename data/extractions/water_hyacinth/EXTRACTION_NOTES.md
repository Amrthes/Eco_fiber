# Water-hyacinth / epoxy tensile extraction

Source ID: `WH-EPOXY-SULARDJAKA-2023`.

## Primary-source access and verification

The published article citation is Sulardjaka, S., Iskandar, N., Manik, P.,
and Nurseto, D. S. (2023), “The effect of alkalization and esterification
treatment on mechanical properties of water hyacinth fiber reinforced
epoxy-resin composite,” *Eastern-European Journal of Enterprise
Technologies*, 1 (12 (121)), 26-33,
https://doi.org/10.15587/1729-4061.2023.274064.

The publisher article page and PDF URL timed out in this environment. OpenAlex
identified a CC BY 4.0 deposit at [Zenodo record 7746959](https://zenodo.org/records/7746959).
Its PDF was downloaded and inspected; a local copy is preserved at
`data/raw/literature/full_text/WH-EPOXY-SULARDJAKA-2023.pdf`. The 2,595,401-byte
file has MD5 `64a04a42aad53169c61316d227a5fbe2`. The paper is eight PDF pages,
journal pages 26-33. The original supplied workbook and its extraction CSVs
were retained unchanged; the normalized literature rows and this review note
now record the primary-source cross-check.

## Material and methods

PDF p.1 (journal p.26) identifies the plant as *Eichhornia crassipes*. PDF
p.3 (journal p.28), Sections 4.2-4.3, describes hair-like strands mechanically
extracted by brushing 50-70 cm stems with an iron brush, then sun-dried. The
matrix is Bakelite EPR 174 epoxy with V-140 hardener. The paper lists 5% and
10% NaOH or esterification for 24 hours, followed by washing and sun-drying.
It describes hand lay-up, 0/15/25/35 wt% fibre configurations, a 250 x 185 x
10 mm mould, 5 MPa compaction, and water-jet cutting. Composite tensile tests
use ASTM D3039; neat epoxy uses ASTM D638. The methods say six specimens were
tested per parameter, but do not state whether tabulated/prose values are
means or give SD/error bars. Fibre length in the final composite is not
reported; the 50-70 cm measurement refers to source stems.

There is an unresolved treatment-description discrepancy: the abstract lists
2%, 5%, and 10% NaOH, while Section 4.2 lists only 5% and 10%. The methods
identify esterification as CH3COOH (acetic acid), while the abstract and
results call it acetate/acetic anhydride. The extraction retains this
ambiguity and does not create a 2% observation.

## Tensile results and reconciliation

PDF p.4 (journal p.29), Section 5.3, and PDF p.6 (journal p.31), Conclusion
3, confirm the six numeric text rows in `observations_verified.csv`:

- 0 wt% point: 41 MPa. The value is reported, but identifying it as a
  matrix-only/neat-epoxy baseline is an inference; it is not counted as a
  fibre-composite observation.
- Untreated water-hyacinth composite: 45 MPa at 25 wt%.
- 5% NaOH-treated composite: 55 MPa at 15 wt% and 58 MPa at 25 wt%.
- Esterified composite: 59 MPa at 15 wt% and 61 MPa at 25 wt%.

The text does not identify a summary statistic for these values. Keep them as
`reported_value`, not individual specimen values or reported means. Their
source remains context-only for EcoFiber AI because water hyacinth is not
*Ipomoea carnea*.

PDF p.5 (journal p.30), Figure 6, was visually inspected. It is an unlabeled
line chart with 10 MPa y-axis grid spacing and no error bars. The four
existing readings in `estimates_graph.csv` remain graph estimates; the three
existing figure sides of the 35 wt% conflicts are also approximate readings.
Do not promote them to directly reported values. The chart shows approximately
54 MPa for untreated, 59 MPa for 5% NaOH, and 42 MPa for 10% NaOH at 35 wt%,
conflicting with the paper's text values of 67, 51, and 35 MPa respectively.
These three disagreements remain separate and unresolved in
`conflicts_text_vs_figure.csv` and the normalized evidence table. The AA
35 wt% chart reading remains approximate; the text says it is about 7% above
61 MPa but gives no exact value.

No paper-specific flexural strength, impact resistance, or water absorption
measurements were found. The paper discusses tensile strength, density,
porosity, fibre thickness, and elongation; none is substituted for another
target.

## Preserved extraction assets and safeguards

- `source_extraction.xlsx` is the supplied original workbook.
- `observations_verified.csv`, `estimates_graph.csv`, and
  `conflicts_text_vs_figure.csv` remain unchanged source-extraction snapshots;
  their original row IDs and provenance are retained.
- The workbook's `Verified` label is not a claim of independent verification.
  Primary-source checks and precise PDF/journal locators are documented above
  and in `source_record.json` and normalized observation `source_locator`
  fields.
- The 0 wt% classification stays inferred; graph values stay estimates; all
  three 35 wt% conflicts stay unresolved. No model eligibility or compatibility
  rule is changed.
