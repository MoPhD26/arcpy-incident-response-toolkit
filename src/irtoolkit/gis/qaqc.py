"""Apply QA/QC rules to a feature class with arcpy.da cursors.

Read mode uses a SearchCursor and changes nothing. Fix mode uses an
UpdateCursor inside an edit session, so it is safe on versioned enterprise
geodatabases. Both modes write a CSV issue report for the data owner.
"""

from __future__ import annotations

import csv
from pathlib import Path

import arcpy

from irtoolkit.logging_utils import get_logger
from irtoolkit.qaqc_rules import Issue, RowRule, Rule, evaluate, required_fields

log = get_logger(__name__)


def run_qaqc(
    feature_class: str,
    rules: list[Rule | RowRule],
    report_csv: str | Path,
    apply_fixes: bool = False,
    where_clause: str | None = None,
) -> list[Issue]:
    d = arcpy.da.Describe(feature_class)
    oid = d["OIDFieldName"]
    existing = {f.name for f in d["fields"]}
    fields = [f for f in required_fields(rules) if f in existing]
    skipped = set(required_fields(rules)) - existing
    if skipped:
        log.warning("Rules reference missing fields, skipped: %s", ", ".join(sorted(skipped)))
    cursor_fields = [oid, *fields]

    issues: list[Issue] = []
    if apply_fixes:
        workspace = d["path"]
        # Walk up from a feature dataset to its geodatabase if needed.
        if arcpy.da.Describe(workspace)["dataType"] == "FeatureDataset":
            workspace = arcpy.da.Describe(workspace)["path"]
        versioned = d.get("isVersioned", False)
        with arcpy.da.Editor(workspace, multiuser_mode=versioned):
            with arcpy.da.UpdateCursor(feature_class, cursor_fields, where_clause) as cur:
                for values in cur:
                    row = dict(zip(cursor_fields, values))
                    fixed, row_issues = evaluate(row, rules, id_field=oid)
                    issues.extend(row_issues)
                    if fixed != row:
                        cur.updateRow([fixed[f] for f in cursor_fields])
    else:
        with arcpy.da.SearchCursor(feature_class, cursor_fields, where_clause) as cur:
            for values in cur:
                _, row_issues = evaluate(dict(zip(cursor_fields, values)), rules, id_field=oid)
                issues.extend(row_issues)

    write_report(issues, report_csv)
    fixed_count = sum(1 for i in issues if i.fixed_to is not None)
    log.info("QA/QC found %d issues, auto fixed %d. Report: %s", len(issues), fixed_count, report_csv)
    return issues


def write_report(issues: list[Issue], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "rule", "field", "value", "message", "fixed_to"])
        for i in issues:
            fixed_to = "" if i.fixed_to is None else i.fixed_to
            w.writerow([i.row_id, i.rule, i.field, i.value, i.message, fixed_to])
