import csv, json, pathlib
D = pathlib.Path(__file__).parent
P = D / "extractions" / "bamboo"
rd = lambda n: list(csv.DictReader(open(P / n)))
V, E = rd("observations_verified.csv"), rd("estimates_graph.csv")
S = json.load(open(P / "source_record.json"))

def test_no_verified_values_without_numeric_text():
    assert len(V) == 0 and S["directly_reported_tensile_values"] == 0

def test_estimates_labelled_and_located():
    assert len(E) == 9
    for r in E:
        assert r["value_basis"] == "graph_estimate" and "p.3" in r["figure_location"]
        assert "0.5" in r["reading_uncertainty"] and r["statistic"].startswith("not stated")

def test_grid_complete_and_monotonic_in_loading():
    g = {(int(r["fibre_length_mm"]), int(r["fibre_loading"])): float(r["value"]) for r in E}
    assert sorted(g) == [(L, w) for L in (6, 8, 12) for w in (15, 30, 45)]
    for L in (6, 8, 12):
        assert g[(L, 15)] <= g[(L, 30)] <= g[(L, 45)]

def test_material_families_not_mixed():
    txt = " ".join(" ".join(r.values()) for r in E).lower()
    assert "hyacinth" not in txt and "ipomoea" not in txt
    assert "NOT water hyacinth" in S["material_family"]

def test_no_specimen_level_claim():
    assert S["specimen_level_data"] is False
