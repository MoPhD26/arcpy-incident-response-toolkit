import pytest
from conftest import SAMPLE_CSV

from irtoolkit.incidents import BoundingBox, load_incidents, missing_columns


def test_sample_file_loads_good_rows_and_rejects_bad_ones():
    result = load_incidents(SAMPLE_CSV)
    assert len(result.incidents) == 25
    assert len(result.rejected) == 5


def test_rejection_reasons_are_specific():
    reasons = " | ".join(r for _, r in load_incidents(SAMPLE_CSV).rejected)
    assert "duplicate incident_id INC-0005" in reasons
    assert "swapped" in reasons
    assert "not numeric" in reasons
    assert "outside response area" in reasons
    assert "missing incident_id" in reasons


def test_categories_are_normalized(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("incident_id,longitude,latitude,category\nA,-97.7,30.3,flooding\n")
    assert load_incidents(f).incidents[0].category == "FLOODING"


def test_header_is_case_insensitive_and_bom_safe(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("﻿Incident_ID,Longitude,Latitude\nA,-97.7,30.3\n", encoding="utf-8")
    assert load_incidents(f).ok


def test_missing_columns_raise(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("id,x,y\n1,2,3\n")
    with pytest.raises(ValueError, match="incident_id"):
        load_incidents(f)


def test_missing_columns_helper():
    assert missing_columns(["Incident_ID", "LATITUDE"]) == ["longitude"]


def test_custom_bbox_and_no_bbox(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("incident_id,longitude,latitude\nA,-80.19,25.76\n")
    assert not load_incidents(f).ok
    assert load_incidents(f, bbox=None).ok
    florida = BoundingBox(-87.6, 24.5, -80.0, 31.0)
    assert load_incidents(f, bbox=florida).ok
