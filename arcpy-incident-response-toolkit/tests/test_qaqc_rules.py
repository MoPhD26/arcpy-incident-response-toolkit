from datetime import date, datetime

from irtoolkit.qaqc_rules import (
    RowRule,
    Rule,
    date_between,
    evaluate,
    in_range,
    one_of,
    required,
    required_fields,
    strip_whitespace,
)
from irtoolkit.shelter_standard import SHELTER_RULES


def test_required():
    check = required()
    assert check("Shelter A") is None
    assert check("  ") is not None
    assert check(None) is not None


def test_one_of_fixes_case():
    check = one_of({"Open", "Closed"})
    assert check("Open") is None
    assert check("OPEN") == ("'OPEN' should be 'Open'", "Open")
    assert check("Maybe")[1] is None


def test_in_range_and_non_numeric():
    check = in_range(0, 10)
    assert check(5) is None
    assert "outside" in check(11)[0]
    assert "not numeric" in check("ten")[0]


def test_date_between_accepts_datetime():
    check = date_between(date(2020, 1, 1), date(2025, 1, 1))
    assert check(datetime(2022, 5, 1, 9, 30)) is None
    assert check(date(2019, 12, 31)) is not None


def test_autofix_only_when_enabled():
    rules_fix = [Rule("trim", "NAME", strip_whitespace(), autofix=True)]
    rules_flag = [Rule("trim", "NAME", strip_whitespace(), autofix=False)]
    fixed, issues = evaluate({"OBJECTID": 1, "NAME": " A "}, rules_fix)
    assert fixed["NAME"] == "A" and issues[0].fixed_to == "A"
    fixed, issues = evaluate({"OBJECTID": 1, "NAME": " A "}, rules_flag)
    assert fixed["NAME"] == " A " and issues[0].fixed_to is None


def test_row_rules_see_fixed_values():
    seen = {}
    rule = RowRule("peek", ("STATUS",), lambda r: seen.setdefault("v", r["STATUS"]) and None)
    evaluate({"STATUS": "OPEN"}, [Rule("s", "STATUS", one_of({"Open"}), autofix=True), rule])
    assert seen["v"] == "Open"


def test_shelter_standard_on_a_messy_row():
    row = {
        "OBJECTID": 7, "NAME": " Eastside Rec Center ", "STATUS": "full",
        "SHELTER_TYPE": "pet friendly", "CAPACITY": 200, "OCCUPANCY": 80,
        "LAST_INSPECTED": date(2010, 3, 1),
    }
    fixed, issues = evaluate(row, SHELTER_RULES)
    rules_hit = {i.rule for i in issues}
    assert fixed["NAME"] == "Eastside Rec Center"
    assert fixed["STATUS"] == "Full"
    assert fixed["SHELTER_TYPE"] == "Pet Friendly"
    assert {"inspection date", "full status check"} <= rules_hit
    assert "occupancy vs capacity" not in rules_hit


def test_over_capacity_is_flagged():
    row = {"OBJECTID": 1, "NAME": "A", "STATUS": "Open", "SHELTER_TYPE": "General",
           "CAPACITY": 100, "OCCUPANCY": 140, "LAST_INSPECTED": date(2024, 1, 1)}
    _, issues = evaluate(row, SHELTER_RULES)
    assert [i.rule for i in issues] == ["occupancy vs capacity"]


def test_missing_fields_are_skipped():
    _, issues = evaluate({"OBJECTID": 1}, SHELTER_RULES)
    assert issues == []


def test_required_fields_are_unique_and_ordered():
    fields = required_fields(SHELTER_RULES)
    assert fields[0] == "NAME"
    assert len(fields) == len(set(fields))
