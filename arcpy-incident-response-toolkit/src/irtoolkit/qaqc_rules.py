"""A small, declarative QA/QC rules engine for attribute data.

Rules are plain Python and work on dictionaries, so they are unit tested
without ArcPy. ``irtoolkit.gis.qaqc`` applies them to a feature class with
cursors. Each rule can only flag a problem, or it can also return a fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Optional

Row = dict[str, Any]
# A check returns None when the row passes, or (message, fixed_value_or_None).
Check = Callable[[Any], Optional[tuple[str, Any]]]


@dataclass(frozen=True)
class Rule:
    name: str
    field: str
    check: Check
    autofix: bool = False


@dataclass(frozen=True)
class RowRule:
    """A rule that compares fields within one row, for example occupancy <= capacity."""

    name: str
    fields: tuple[str, ...]
    check: Callable[[Row], Optional[str]]


@dataclass(frozen=True)
class Issue:
    row_id: Any
    rule: str
    field: str
    value: Any
    message: str
    fixed_to: Any = None


# ---------- reusable check factories ----------

def required() -> Check:
    def _check(v: Any):
        if v is None or (isinstance(v, str) and not v.strip()):
            return ("value is required", None)
        return None
    return _check


def one_of(allowed: set[str], normalize: bool = True) -> Check:
    lookup = {a.upper(): a for a in allowed}

    def _check(v: Any):
        if v is None:
            return None
        if v in allowed:
            return None
        if normalize and isinstance(v, str) and v.strip().upper() in lookup:
            return (f"'{v}' should be '{lookup[v.strip().upper()]}'", lookup[v.strip().upper()])
        return (f"'{v}' is not an allowed value", None)
    return _check


def in_range(lo: float, hi: float) -> Check:
    def _check(v: Any):
        if v is None:
            return None
        try:
            num = float(v)
        except (TypeError, ValueError):
            return (f"'{v}' is not numeric", None)
        if not lo <= num <= hi:
            return (f"{num} is outside {lo} to {hi}", None)
        return None
    return _check


def date_between(start: date, end: date) -> Check:
    def _check(v: Any):
        if v is None:
            return None
        d = v.date() if isinstance(v, datetime) else v
        if not start <= d <= end:
            return (f"{d} is outside {start} to {end}", None)
        return None
    return _check


def strip_whitespace() -> Check:
    def _check(v: Any):
        if isinstance(v, str) and v != v.strip():
            return ("leading or trailing spaces", v.strip())
        return None
    return _check


# ---------- engine ----------

def evaluate(
    row: Row, rules: list[Rule | RowRule], id_field: str = "OBJECTID"
) -> tuple[Row, list[Issue]]:
    """Check one row against every rule. Returns the (possibly fixed) row and its issues.

    Field rules run first so row rules see cleaned values.
    """
    fixed = dict(row)
    issues: list[Issue] = []
    for rule in [r for r in rules if isinstance(r, Rule)]:
        if rule.field not in fixed:
            continue
        outcome = rule.check(fixed[rule.field])
        if outcome is None:
            continue
        message, fix = outcome
        applied = fix if (rule.autofix and fix is not None) else None
        issues.append(Issue(row.get(id_field), rule.name, rule.field, fixed[rule.field], message, applied))
        if applied is not None:
            fixed[rule.field] = applied
    for rule in [r for r in rules if isinstance(r, RowRule)]:
        if not all(f in fixed for f in rule.fields):
            continue
        message = rule.check(fixed)
        if message:
            issues.append(Issue(row.get(id_field), rule.name, ",".join(rule.fields), None, message))
    return fixed, issues


def required_fields(rules: list[Rule | RowRule]) -> list[str]:
    """Unique field names the rules touch, in first-seen order."""
    names: list[str] = []
    for r in rules:
        names.extend([r.field] if isinstance(r, Rule) else r.fields)
    return list(dict.fromkeys(names))
