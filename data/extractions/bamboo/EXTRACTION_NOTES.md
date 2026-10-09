# Bamboo / epoxy tensile extraction

Source: M. Ramarao, A. Ravi Kiran, G. Mallikharjuna, B. Jamal Vali, and
J. V. Mohanachari, 2018, *Journal of Advancement in Engineering and
Technology*, 6(1), V6I1.01, DOI 10.5281/zenodo.1163658. The citation and
four-page published PDF were checked using the open Zenodo record
<https://zenodo.org/records/1163658> (CC BY 4.0); PDF pages 1-4 were inspected
on 2026-10-09. Bamboo evidence remains separate from water hyacinth and
Ipomoea carnea.

Result: 0 numeric tensile values reported in text or a results table; 9
approximate graph readings from the unnumbered tensile chart (PDF p.3, Sec.
5.1), with the bundle's stated +/-0.5 MPa reading uncertainty. The chart image
was re-read against its 2 MPa vertical grid; all nine existing values agree
with the bar tops. They remain graph estimates, not directly reported values
or verified specimen measurements.

Full-text checks:
- PDF p.1 lists all five authors, the title, journal, volume/issue, and
  a publication date of 10 January 2018. The journal citation and DOI are
  repeated on p.4. Zenodo's record lists an issue date of 31 January 2018 and
  only J. V. Mohanachari as creator; the paper itself lists the five-author
  byline. The year and paper byline are clear; the record-date difference is
  retained.
- PDF p.2, Sec. 3, describes manually cut bamboo fibres of 4, 7, and 10 mm
  and composites at 10, 20, and 30 wt%. Table 1 on p.2 instead specifies 6,
  8, and 12 mm and 15, 30, and 45 wt%. The conflict is unresolved; the
  estimates retain the chart/Table 1 conditions and must be interpreted with
  this caveat.
- PDF p.2 identifies epoxy resin and HY 951 hardener, a 200 x 200 x 40 mm
  wooden mould, a 50 kg dead load for 24 hours, and an additional 24-hour air
  cure. The resin-to-hardener ratio is not given. It names ASTM D3039-76 for
  tensile testing and a Tinius Olsen H10KS instrument.
- PDF p.3 says properties are "tabulated below", but the numerical results
  table is absent. The tensile and hardness charts are present; flexural and
  impact results are not provided. No replicate count, uncertainty bars, or
  specimen-level records are reported.
- No numeric value was transcribed from chart pixels as a directly reported
  value; all nine values retain `graph_estimate` evidence classification.
- PDF p.3, Sec. 5.1, shows lengths 6/8/12 mm on the horizontal axis, 15/30/45
  wt% in the legend, and a 0-20 MPa vertical axis with 2 MPa grid spacing.
  Visual re-reading confirms the 6 mm readings 12/13/14 MPa, 8 mm readings
  14/15/16 MPa, and 12 mm readings 16/18/19 MPa for 15/30/45 wt%,
  respectively. This confirms the supplied estimates against the figure; it
  does not turn them into text-reported measurements or resolve the prose vs.
  Table 1/chart condition conflict.
- Zenodo's API metadata gives J. V. Mohanachari as the deposited-record
  creator; the article's own byline (PDF p.1) is used for the full author list.

Limitations:
- No error bars or replicate count; no neat-epoxy baseline, crosshead speed,
  specimen geometry or epoxy:hardener ratio.
- Fibre length and loading conflict between Sec. 3 text and Table 1/chart as
  described above.
- No chemical treatment is described, so treatment is "none stated", not
  "untreated" confirmed.
- Flexural and impact results are claimed but absent. The hardness chart is
  outside the current prediction targets.
- No specimen-level data.
- The source remains `context only` and `pending` in the source register
  because bamboo is a different fibre species, not because its paper is still
  uninspected. Its graph estimates remain ineligible for model training.
