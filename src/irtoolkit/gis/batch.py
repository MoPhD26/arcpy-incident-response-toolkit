"""Batch processing with list functions and loops.

Agencies receive data from partners in mixed coordinate systems. This module
inventories a workspace and projects everything to one target, skipping data
that is already correct and logging every decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import arcpy

from irtoolkit.logging_utils import get_logger

log = get_logger(__name__)


@dataclass
class BatchReport:
    projected: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    def summary(self) -> str:
        return (f"projected {len(self.projected)}, skipped {len(self.skipped)}, "
                f"failed {len(self.failed)}")


def inventory(workspace: str, wildcard: str = "*", feature_type: str = "") -> dict[str, list[str]]:
    """List every feature class in a workspace, including inside feature datasets."""
    arcpy.env.workspace = workspace
    found: dict[str, list[str]] = {"<root>": arcpy.ListFeatureClasses(wildcard, feature_type) or []}
    for fds in arcpy.ListDatasets(feature_type="Feature") or []:
        found[fds] = arcpy.ListFeatureClasses(wildcard, feature_type, fds) or []
    total = sum(len(v) for v in found.values())
    log.info("Found %d feature classes in %s", total, workspace)
    return found


def batch_project(
    in_workspace: str,
    out_workspace: str,
    target_sr: arcpy.SpatialReference | int | str,
    wildcard: str = "*",
    suffix: str = "_proj",
) -> BatchReport:
    """Project every matching feature class into ``target_sr``.

    ``target_sr`` can be a WKID, a SpatialReference, or a dataset to match.
    """
    if isinstance(target_sr, int):
        target_sr = arcpy.SpatialReference(target_sr)
    elif isinstance(target_sr, str):
        target_sr = arcpy.da.Describe(target_sr)["spatialReference"]

    report = BatchReport()
    arcpy.env.workspace = in_workspace
    for fc in arcpy.ListFeatureClasses(wildcard) or []:
        current = arcpy.da.Describe(fc)["spatialReference"]
        if current.factoryCode == target_sr.factoryCode:
            log.info("Skip %s: already in %s", fc, target_sr.name)
            report.skipped.append(fc)
            continue
        out_fc = f"{out_workspace}\\{fc}{suffix}"
        try:
            arcpy.management.Project(fc, out_fc, target_sr)
            log.info("Projected %s from %s to %s", fc, current.name, target_sr.name)
            report.projected.append(out_fc)
        except arcpy.ExecuteError:
            msg = arcpy.GetMessages(2)
            log.error("Failed %s: %s", fc, msg)
            report.failed.append((fc, msg))

    log.info("Batch complete: %s", report.summary())
    return report
