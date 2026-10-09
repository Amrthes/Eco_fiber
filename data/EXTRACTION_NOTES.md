# Source-separated extraction bundles

The extraction-specific tests and evidence bundles live under
`data/extractions/`, outside the project audit's raw and processed data roots.
This prevents staged evidence from being counted again beside its normalized
records in `data/raw/literature/literature_observations.csv`.

- `data/extractions/water_hyacinth/` contains the water-hyacinth workbook and
  distinct text-reported, graph-estimate, conflict, and source-record files.
- `data/extractions/bamboo/` contains the bamboo text-reported header-only
  file, nine graph estimates, source record, and internal inconsistencies.
- Existing root-level extraction files are preserved as received: the
  root-level estimates and source record are bamboo evidence, while
  `conflicts_text_vs_figure.csv` and the supplied workbook are
  water-hyacinth evidence. These legacy files are not the test inputs.

Both sources remain context-only. The bamboo paper is full-text inspected and
its nine chart estimates have been visually rechecked against the figure; they
remain estimates. The water-hyacinth paper was obtained from Zenodo record
7746959 under CC BY 4.0 and is retained under
`data/raw/literature/full_text/`. Its six text-value rows were checked against
the paper; three 35 wt% text/Figure 6 conflicts remain unresolved. Graph
readings remain estimates, and the inferred matrix-only classification at
0 wt% is not a directly reported material classification. Neither source is
eligible for modelling because neither is *Ipomoea carnea* evidence and both
remain context-only.
