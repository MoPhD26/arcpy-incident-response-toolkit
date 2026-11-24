"""Build an incident impact area from geometry objects and find affected features.

Workflow:
1. Validated incident points become an arcpy.Multipoint.
2. The impact area is a buffered convex hull (or a plain buffer for one point).
3. A SearchCursor tests each address point against the area with geometry
   methods, and an InsertCursor writes the matches to a notification layer.

Geometry objects are used directly, so no intermediate datasets are written.
"""

from __future__ import annotations

import arcpy

from irtoolkit.incidents import Incident
from irtoolkit.logging_utils import get_logger

log = get_logger(__name__)
WGS84 = 4326

# arcpy.Field.type values mapped to the keywords AddFields expects.
FIELD_TYPE_MAP = {
    "String": "TEXT", "Integer": "LONG", "SmallInteger": "SHORT", "BigInteger": "BIGINTEGER",
    "Double": "DOUBLE", "Single": "FLOAT", "Date": "DATE", "DateOnly": "DATEONLY",
    "GUID": "GUID",
}


def incidents_to_multipoint(incidents: list[Incident]) -> arcpy.Multipoint:
    arr = arcpy.Array([arcpy.Point(i.longitude, i.latitude) for i in incidents])
    return arcpy.Multipoint(arr, arcpy.SpatialReference(WGS84))


def impact_area(incidents: list[Incident], buffer_distance: float, work_wkid: int) -> arcpy.Polygon:
    """Return a polygon covering all incidents plus a safety buffer.

    Geometry is projected to ``work_wkid`` (a projected system in meters or
    feet) before buffering so distances are measured correctly.
    """
    if not incidents:
        raise ValueError("At least one incident is required")
    mp = incidents_to_multipoint(incidents).projectAs(arcpy.SpatialReference(work_wkid))
    base = mp.convexHull() if len(incidents) >= 3 else mp
    area = base.buffer(buffer_distance)
    log.info("Impact area from %d incidents covers %.0f square units", len(incidents), area.area)
    return area


def affected_features(
    area: arcpy.Polygon,
    source_fc: str,
    out_fc: str,
    keep_fields: list[str],
) -> int:
    """Copy features from ``source_fc`` that fall inside ``area`` into ``out_fc``."""
    src = arcpy.da.Describe(source_fc)
    area = area.projectAs(src["spatialReference"])
    out_path, out_name = out_fc.rsplit("\\", 1) if "\\" in out_fc else out_fc.rsplit("/", 1)

    arcpy.management.CreateFeatureclass(
        out_path, out_name, src["shapeType"], spatial_reference=src["spatialReference"]
    )
    field_defs = {f.name: f for f in src["fields"]}
    arcpy.management.AddFields(
        out_fc,
        [[n, FIELD_TYPE_MAP.get(field_defs[n].type, "TEXT"), field_defs[n].aliasName or n,
          field_defs[n].length] for n in keep_fields],
    )

    cursor_fields = ["SHAPE@", *keep_fields]
    count = 0
    # Spatial filter in the cursor narrows candidates, the geometry test confirms.
    with arcpy.da.SearchCursor(source_fc, cursor_fields, spatial_filter=area,
                               spatial_relationship="INTERSECTS") as s_cur, \
         arcpy.da.InsertCursor(out_fc, cursor_fields) as i_cur:
        for row in s_cur:
            if not row[0].disjoint(area):
                i_cur.insertRow(row)
                count += 1
    log.info("%d affected features written to %s", count, out_fc)
    return count
