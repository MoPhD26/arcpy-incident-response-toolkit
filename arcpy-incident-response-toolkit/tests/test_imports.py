"""Smoke test: every ArcPy module imports cleanly (against the stub in CI)."""

import importlib

import pytest


@pytest.mark.parametrize("module", [
    "irtoolkit.gis.describe",
    "irtoolkit.gis.batch",
    "irtoolkit.gis.qaqc",
    "irtoolkit.gis.impact",
    "irtoolkit.logging_utils",
])
def test_module_imports(module):
    importlib.import_module(module)
