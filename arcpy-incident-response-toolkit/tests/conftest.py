"""Test setup.

Pure modules are tested directly. For modules that import ArcPy, a stub
module is registered so CI (which has no ArcGIS license) can still import
them and check they load cleanly.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "arcpy" not in sys.modules:
    try:
        import arcpy  # noqa: F401
    except ImportError:
        stub = types.ModuleType("arcpy")
        stub.da = types.SimpleNamespace()
        stub.management = types.SimpleNamespace()
        stub.env = types.SimpleNamespace()
        stub.SpatialReference = object
        stub.Multipoint = object
        stub.Polygon = object
        stub.ExecuteError = type("ExecuteError", (Exception,), {})
        sys.modules["arcpy"] = stub

SAMPLE_CSV = ROOT / "data" / "sample_incidents.csv"
