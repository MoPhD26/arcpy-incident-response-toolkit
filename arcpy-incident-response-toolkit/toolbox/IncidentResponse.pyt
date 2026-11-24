# -*- coding: utf-8 -*-
"""Incident Response Toolbox for ArcGIS Pro.

A Python toolbox (.pyt) is plain text, so the tool interface, validation,
and execution are all reviewable in version control.

Tools
    1. Validate Incident Report   checks a field CSV before anyone maps it
    2. Map Incident Impact Area   builds the impact area and the notification list
    3. Run Attribute QA/QC        flags or fixes attribute problems with cursors
"""

import os
import sys

import arcpy

# Make the irtoolkit package importable when the toolbox is opened in Pro.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import importlib  # noqa: E402

import irtoolkit.incidents as incidents  # noqa: E402
import irtoolkit.qaqc_rules as rules_mod  # noqa: E402

# Reload so edits to the package show up without restarting ArcGIS Pro.
importlib.reload(incidents)
importlib.reload(rules_mod)


class Toolbox:
    def __init__(self):
        self.label = "Incident Response Toolkit"
        self.alias = "incidentresponse"
        self.tools = [ValidateIncidentReport, MapIncidentImpact, RunAttributeQAQC]


def _csv_header(path):
    import csv
    with open(path, newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


class ValidateIncidentReport:
    def __init__(self):
        self.label = "Validate Incident Report"
        self.description = ("Checks an incident CSV for missing, duplicate, swapped, "
                            "or out of area coordinates.")
        self.category = "1. Intake"

    def getParameterInfo(self):
        in_csv = arcpy.Parameter(displayName="Incident CSV", name="in_csv",
                                 datatype="DEFile", parameterType="Required", direction="Input")
        in_csv.filter.list = ["csv"]
        out_report = arcpy.Parameter(displayName="Rejected Rows Report", name="out_report",
                                     datatype="DEFile", parameterType="Optional", direction="Output")
        out_report.filter.list = ["csv"]
        return [in_csv, out_report]

    def updateParameters(self, parameters):
        in_csv, out_report = parameters
        # Suggest a report name next to the input the first time a CSV is chosen.
        if in_csv.altered and in_csv.valueAsText and not out_report.altered:
            base, _ = os.path.splitext(in_csv.valueAsText)
            out_report.value = f"{base}_rejected.csv"

    def updateMessages(self, parameters):
        in_csv = parameters[0]
        if in_csv.valueAsText and os.path.exists(in_csv.valueAsText):
            missing = incidents.missing_columns(_csv_header(in_csv.valueAsText))
            if missing:
                in_csv.setErrorMessage(f"Missing required columns: {', '.join(missing)}")

    def execute(self, parameters, messages):
        in_csv, out_report = (p.valueAsText for p in parameters)
        result = incidents.load_incidents(in_csv)
        arcpy.AddMessage(result.summary())
        for line_no, reason in result.rejected:
            arcpy.AddWarning(f"Line {line_no}: {reason}")
        if out_report:
            import csv
            with open(out_report, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["line", "reason"])
                w.writerows(result.rejected)
            arcpy.AddMessage(f"Report written to {out_report}")


class MapIncidentImpact:
    def __init__(self):
        self.label = "Map Incident Impact Area"
        self.description = ("Builds a buffered convex hull around incident points and lists "
                            "every address point inside it for notification.")
        self.category = "2. Response"

    def getParameterInfo(self):
        in_csv = arcpy.Parameter(displayName="Incident CSV", name="in_csv",
                                 datatype="DEFile", parameterType="Required", direction="Input")
        in_csv.filter.list = ["csv"]
        buffer_dist = arcpy.Parameter(displayName="Safety Buffer", name="buffer_dist",
                                      datatype="GPLinearUnit", parameterType="Required", direction="Input")
        buffer_dist.value = "500 Meters"
        address_fc = arcpy.Parameter(displayName="Address Points", name="address_fc",
                                     datatype="GPFeatureLayer", parameterType="Required", direction="Input")
        address_fc.filter.list = ["Point"]
        keep = arcpy.Parameter(displayName="Fields to Keep", name="keep_fields",
                               datatype="Field", parameterType="Required", direction="Input",
                               multiValue=True)
        keep.parameterDependencies = [address_fc.name]
        out_area = arcpy.Parameter(displayName="Output Impact Area", name="out_area",
                                   datatype="DEFeatureClass", parameterType="Required", direction="Output")
        out_notify = arcpy.Parameter(displayName="Output Notification Points", name="out_notify",
                                     datatype="DEFeatureClass", parameterType="Required", direction="Output")
        work_sr = arcpy.Parameter(displayName="Projected Coordinate System for Measuring",
                                  name="work_sr", datatype="GPSpatialReference",
                                  parameterType="Required", direction="Input")
        work_sr.value = arcpy.SpatialReference(3083)  # NAD 1983 Texas Centric Albers Equal Area
        return [in_csv, buffer_dist, address_fc, keep, out_area, out_notify, work_sr]

    def updateMessages(self, parameters):
        in_csv, buffer_dist, *_, work_sr = parameters
        if in_csv.valueAsText and os.path.exists(in_csv.valueAsText):
            missing = incidents.missing_columns(_csv_header(in_csv.valueAsText))
            if missing:
                in_csv.setErrorMessage(f"Missing required columns: {', '.join(missing)}")
        if buffer_dist.valueAsText:
            value = float(buffer_dist.valueAsText.split()[0])
            if value <= 0:
                buffer_dist.setErrorMessage("Buffer distance must be greater than zero.")
            elif value > 50 and "Mile" in buffer_dist.valueAsText:
                buffer_dist.setWarningMessage("That is a very large buffer. Check the units.")
        if work_sr.value and work_sr.value.type != "Projected":
            work_sr.setErrorMessage("Choose a projected coordinate system so distances are accurate.")

    def execute(self, parameters, messages):
        from irtoolkit.gis.impact import affected_features, impact_area

        in_csv = parameters[0].valueAsText
        dist_value, dist_unit = parameters[1].valueAsText.split(maxsplit=1)
        address_fc = parameters[2].valueAsText
        keep_fields = parameters[3].valueAsText.split(";")
        out_area, out_notify = parameters[4].valueAsText, parameters[5].valueAsText
        work_sr = parameters[6].value

        loaded = incidents.load_incidents(in_csv)
        arcpy.AddMessage(loaded.summary())
        for line_no, reason in loaded.rejected:
            arcpy.AddWarning(f"Skipped line {line_no}: {reason}")
        if not loaded.ok:
            arcpy.AddError("No valid incidents to map.")
            return

        # Convert the buffer into the units of the working coordinate system.
        dist = float(dist_value) * arcpy.LinearUnitConversionFactor(dist_unit, work_sr.linearUnitName)
        area = impact_area(loaded.incidents, dist, work_sr.factoryCode)
        arcpy.management.CopyFeatures(area, out_area)
        count = affected_features(area, address_fc, out_notify, keep_fields)
        arcpy.AddMessage(f"{count} address points need notification.")


class RunAttributeQAQC:
    def __init__(self):
        self.label = "Run Attribute QA/QC"
        self.description = ("Checks a shelter or facility layer against data standards "
                            "and writes an issue report.")
        self.category = "3. Data Quality"

    def getParameterInfo(self):
        in_fc = arcpy.Parameter(displayName="Facilities Layer", name="in_fc",
                                datatype="GPFeatureLayer", parameterType="Required", direction="Input")
        report = arcpy.Parameter(displayName="Issue Report", name="report",
                                 datatype="DEFile", parameterType="Required", direction="Output")
        report.filter.list = ["csv"]
        fix = arcpy.Parameter(displayName="Apply automatic fixes", name="fix",
                              datatype="GPBoolean", parameterType="Optional", direction="Input")
        fix.value = False
        return [in_fc, report, fix]

    def updateMessages(self, parameters):
        if parameters[2].value:
            parameters[2].setWarningMessage(
                "Fixes edit the data in place. Run once without fixes to review the report first.")

    def execute(self, parameters, messages):
        from irtoolkit.gis.qaqc import run_qaqc
        from irtoolkit.shelter_standard import SHELTER_RULES

        issues = run_qaqc(parameters[0].valueAsText, SHELTER_RULES,
                          parameters[1].valueAsText, apply_fixes=bool(parameters[2].value))
        arcpy.AddMessage(f"{len(issues)} issues written to {parameters[1].valueAsText}")
