"""Tests for the Streamlit dashboard application using AppTest."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

DASHBOARD_PATH = str(Path(__file__).parents[1] / "dashboard" / "app.py")


def test_dashboard_runs_without_exceptions_in_demo_and_strict_mode():
    """Verify that the 5-tab dashboard runs cleanly in both demo and strict mode."""
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.tabs) == 5

    # Toggle to strict mode
    assert len(at.toggle) >= 1
    at.toggle[0].set_value(False).run()
    assert not at.exception


def test_dashboard_experimental_studio_csv_upload():
    """Verify that uploading a CSV in Tab 5 runs validation and reports status."""
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    valid_csv = Path(__file__).parent / "fixtures" / "valid_artificial.csv"
    assert valid_csv.is_file()

    assert len(at.file_uploader) >= 1
    at.file_uploader[0].upload(filename=valid_csv.name, content=valid_csv.read_bytes()).run()
    assert not at.exception
    assert len(at.success) >= 1
    assert "valid" in at.success[0].value.lower()


