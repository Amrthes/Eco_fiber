import csv, json, pathlib
D = pathlib.Path(__file__).parent
P = D / "extractions" / "water_hyacinth"
rd = lambda n: list(csv.DictReader(open(P / n)))
V, E, C = rd("observations_verified.csv"), rd("estimates_graph.csv"), rd("conflicts_text_vs_figure.csv")

def test_counts():
    assert len(V) == 6 and sum(r["is_fibre_composite"] == "True" for r in V) == 5
    assert len(E) == 4 and len(C) == 4

def test_verified_are_text_reported_and_crosschecked():
    for r in V:
        assert r["value_basis"] == "directly_reported_text"
        assert "agree" in r["crosscheck"] and r["text_location"] and r["figure_location"]

def test_estimates_labelled_and_located():
    for r in E:
        assert r["value_basis"] == "graph_estimate" and r["figure_location"].startswith("Fig. 6")

def test_no_conflicted_35wt_in_verified():
    assert not [r for r in V if r["fibre_loading"] == "35" and r["treatment_type"] != "esterification"]
    assert not [r for r in V if r["fibre_loading"] == "35"]

def test_no_ipomoea_mixing():
    for r in V + E:
        assert "ipomoea" not in " ".join(r.values()).lower()
    assert "NOT Ipomoea" in json.load(open(P / "source_record.json"))["material_family"]

def test_no_specimen_level_claim():
    s = json.load(open(P / "source_record.json"))
    assert s["specimen_level_data"] is False
    assert all(r["statistic"].startswith("not stated") for r in V + E)
