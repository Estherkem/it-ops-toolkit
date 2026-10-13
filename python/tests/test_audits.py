import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asset_register_check import check, net_price  # noqa: E402
from workspace_user_audit import audit  # noqa: E402

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def row(**kw):
    base = {"primaryEmail": "u@example.com", "suspended": "False", "isAdmin": "False",
            "isEnrolledIn2Sv": "True", "lastLoginTime": "2026-10-12T00:00:00.000Z"}
    base.update(kw)
    return base


def issues_for(r):
    return [f.issue for f in audit([r], 90, NOW)]


def test_healthy_user_has_no_findings():
    assert issues_for(row()) == []


def test_admin_without_2sv_is_high():
    findings = audit([row(isAdmin="True", isEnrolledIn2Sv="False")], 90, NOW)
    assert findings[0].severity == "HIGH"


def test_inactive_and_never_logged_in():
    assert "Inactive" in issues_for(row(lastLoginTime="2026-01-01T00:00:00.000Z"))
    assert "Never signed in" in issues_for(row(lastLoginTime="1970-01-01T00:00:00.000Z"))


def test_suspended_only_reports_licence():
    assert issues_for(row(suspended="True", isEnrolledIn2Sv="False")) == ["Suspended account"]


def test_vat_backed_out_only_when_flagged():
    assert net_price({"price": "120", "price_includes_vat": "yes"}, 20) == 100.0
    assert net_price({"price": "120", "price_includes_vat": "no"}, 20) == 120.0


def test_asset_checks():
    rows = [
        {"asset_tag": "A", "serial": "X1", "assigned_to": "a", "warranty_end": "2026-10-20",
         "purchase_date": "2020-01-01", "category": "Laptop", "price": "100"},
        {"asset_tag": "B", "serial": "X1", "assigned_to": "", "category": "Laptop", "price": "50"},
    ]
    issues, costs = check(rows, date(2026, 10, 13))
    text = "\n".join(issues)
    assert "duplicate serial" in text
    assert "not assigned" in text
    assert "warranty expires in 7 days" in text
    assert "refresh cycle" in text
    assert costs["Laptop"] == 150.0
