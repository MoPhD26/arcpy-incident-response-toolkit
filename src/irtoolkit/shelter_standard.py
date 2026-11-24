"""Example data standard: an emergency shelter inventory.

Shows how an organization encodes its schema rules once and reuses them in
the toolbox, in notebooks, and in scheduled jobs.
"""

from __future__ import annotations

from datetime import date

from irtoolkit.qaqc_rules import (
    Row,
    RowRule,
    Rule,
    date_between,
    in_range,
    one_of,
    required,
    strip_whitespace,
)

SHELTER_STATUS = {"Open", "Closed", "Standby", "Full"}
SHELTER_TYPE = {"General", "Medical Needs", "Pet Friendly", "Cooling Center", "Warming Center"}


def _occupancy_within_capacity(row: Row) -> str | None:
    occ, cap = row.get("OCCUPANCY"), row.get("CAPACITY")
    if occ is not None and cap is not None and occ > cap:
        return f"occupancy {occ} exceeds capacity {cap}"
    return None


def _full_means_full(row: Row) -> str | None:
    if row.get("STATUS") == "Full" and row.get("OCCUPANCY") is not None \
            and row.get("CAPACITY") and row["OCCUPANCY"] < 0.9 * row["CAPACITY"]:
        return "status is Full but occupancy is under 90 percent of capacity"
    return None


SHELTER_RULES: list[Rule | RowRule] = [
    Rule("name required", "NAME", required()),
    Rule("name spacing", "NAME", strip_whitespace(), autofix=True),
    Rule("status domain", "STATUS", one_of(SHELTER_STATUS), autofix=True),
    Rule("type domain", "SHELTER_TYPE", one_of(SHELTER_TYPE), autofix=True),
    Rule("capacity range", "CAPACITY", in_range(1, 20000)),
    Rule("occupancy range", "OCCUPANCY", in_range(0, 20000)),
    Rule("inspection date", "LAST_INSPECTED", date_between(date(2015, 1, 1), date.today())),
    RowRule("occupancy vs capacity", ("OCCUPANCY", "CAPACITY"), _occupancy_within_capacity),
    RowRule("full status check", ("STATUS", "OCCUPANCY", "CAPACITY"), _full_means_full),
]
