"""Logging that works both in a terminal and inside ArcGIS Pro script tools."""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


class ArcPyMessageHandler(logging.Handler):
    """Forward log records to the ArcGIS Pro geoprocessing messages pane."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import arcpy  # noqa: PLC0415
        except ImportError:
            return
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            arcpy.AddError(msg)
        elif record.levelno >= logging.WARNING:
            arcpy.AddWarning(msg)
        else:
            arcpy.AddMessage(msg)


def get_logger(name: str = "irtoolkit", to_arcpy: bool = False) -> logging.Logger:
    """Return a configured logger. Set ``to_arcpy`` inside script tools."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler: logging.Handler = ArcPyMessageHandler() if to_arcpy else logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s" if to_arcpy else _FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
