"""Read and validate incident report CSV files.

Field crews and call centers send incident locations as CSV. Real files are
messy: missing coordinates, swapped lat/lon, duplicates, and points far
outside the response area. This module catches those problems before any
geometry is built, and reports every rejected row with a reason.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = ("incident_id", "longitude", "latitude")


@dataclass(frozen=True)
class Incident:
    incident_id: str
    longitude: float
    latitude: float
    category: str = "UNKNOWN"
    reported: str = ""


@dataclass
class IncidentLoadResult:
    incidents: list[Incident] = field(default_factory=list)
    rejected: list[tuple[int, str]] = field(default_factory=list)  # (line number, reason)

    @property
    def ok(self) -> bool:
        return bool(self.incidents)

    def summary(self) -> str:
        return f"{len(self.incidents)} incidents loaded, {len(self.rejected)} rows rejected"


@dataclass(frozen=True)
class BoundingBox:
    """Geographic extent used to reject points outside the response area."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def contains(self, lon: float, lat: float) -> bool:
        return self.xmin <= lon <= self.xmax and self.ymin <= lat <= self.ymax


# Rough extent of Texas, used as a sensible default for this project.
TEXAS_BBOX = BoundingBox(-106.65, 25.84, -93.51, 36.50)


def missing_columns(header: list[str]) -> list[str]:
    """Return required columns absent from a CSV header (case insensitive)."""
    present = {h.strip().lower() for h in header}
    return [c for c in REQUIRED_COLUMNS if c not in present]


def _looks_swapped(lon: float, lat: float, bbox: BoundingBox | None) -> bool:
    """True when the values only make sense with longitude and latitude exchanged."""
    if bbox and not bbox.contains(lon, lat):
        return bbox.contains(lat, lon)
    return not (-90 <= lat <= 90) and (-90 <= lon <= 90)


def load_incidents(path: str | Path, bbox: BoundingBox | None = TEXAS_BBOX) -> IncidentLoadResult:
    """Parse an incident CSV into validated ``Incident`` records.

    Rows are rejected, not silently dropped, so the caller can report them.
    """
    result = IncidentLoadResult()
    seen: set[str] = set()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = missing_columns(header)
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

        for line_no, raw in enumerate(reader, start=2):
            row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
            iid = row["incident_id"]
            if not iid:
                result.rejected.append((line_no, "missing incident_id"))
                continue
            if iid in seen:
                result.rejected.append((line_no, f"duplicate incident_id {iid}"))
                continue
            try:
                lon, lat = float(row["longitude"]), float(row["latitude"])
            except ValueError:
                result.rejected.append((line_no, "coordinates are not numeric"))
                continue
            # A common field error is swapped columns. Name it explicitly.
            swapped = _looks_swapped(lon, lat, bbox)
            hint = " (latitude and longitude look swapped)" if swapped else ""
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                result.rejected.append((line_no, f"coordinates out of valid range{hint}"))
                continue
            if bbox and not bbox.contains(lon, lat):
                result.rejected.append((line_no, f"outside response area{hint}"))
                continue

            seen.add(iid)
            result.incidents.append(
                Incident(
                    incident_id=iid,
                    longitude=lon,
                    latitude=lat,
                    category=(row.get("category") or "UNKNOWN").upper(),
                    reported=row.get("reported", ""),
                )
            )
    return result
