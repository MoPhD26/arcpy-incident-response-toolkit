"""Inspect datasets with arcpy.da.Describe and build new data from their properties."""

from __future__ import annotations

from pathlib import Path

import arcpy

from irtoolkit.logging_utils import get_logger

log = get_logger(__name__)


def dataset_profile(dataset: str) -> dict:
    """Return a compact, readable summary of a feature class or table."""
    d = arcpy.da.Describe(dataset)
    sr = d.get("spatialReference")
    return {
        "name": d["baseName"],
        "path": d["path"],
        "data_type": d["dataType"],
        "shape_type": d.get("shapeType"),
        "spatial_reference": sr.name if sr else None,
        "wkid": sr.factoryCode if sr else None,
        "fields": [f.name for f in d.get("fields", [])],
        "has_m": d.get("hasM"),
        "has_z": d.get("hasZ"),
    }


def clone_empty(template: str, out_name: str | None = None, out_path: str | None = None) -> str:
    """Create an empty feature class that copies a template's geometry type,
    spatial reference, and schema. Useful for staging incoming field data.
    """
    d = arcpy.da.Describe(template)
    out_path = out_path or d["path"]
    out_name = out_name or f"{d['baseName']}_staging"
    result = arcpy.management.CreateFeatureclass(
        out_path=out_path,
        out_name=out_name,
        geometry_type=d["shapeType"],
        template=template,
        has_m="ENABLED" if d.get("hasM") else "DISABLED",
        has_z="ENABLED" if d.get("hasZ") else "DISABLED",
        spatial_reference=d["spatialReference"],
    )
    out = str(Path(out_path) / out_name)
    log.info("Created %s from template %s", out, d["baseName"])
    return result[0]
