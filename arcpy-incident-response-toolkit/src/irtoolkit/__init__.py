"""Incident Response Toolkit: ArcPy automation for emergency GIS workflows.

Pure Python logic (incident parsing, QA/QC rules) lives at the package root
so it can be unit tested anywhere. Everything that needs ArcPy lives in
``irtoolkit.gis`` and imports ArcPy lazily.
"""

__version__ = "1.0.0"
