"""Audit a Google Workspace user export for common security and licence issues.

Reads a CSV of users (e.g. from `gam print users fields ...` or the Admin console
export) and flags:
  - active accounts with 2-Step Verification not enrolled
  - active accounts not signed in for N days (licence waste / departed staff)
  - accounts that have never signed in
  - suspended accounts still holding a licence slot
  - admins without 2SV (highlighted separately)

Usage:
    python workspace_user_audit.py ../samples/users.csv
    python workspace_user_audit.py users.csv --inactive-days 60 --out report.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

# Column names differ between GAM and the Admin console export; accept either.
COLUMN_ALIASES = {
    "email": ["primaryEmail", "Email Address [Required]", "email"],
    "suspended": ["suspended", "Status [READ ONLY]"],
    "is_admin": ["isAdmin", "Admin"],
    "enrolled_2sv": ["isEnrolledIn2Sv", "2sv Enrolled [READ ONLY]"],
    "last_login": ["lastLoginTime", "Last Sign In [READ ONLY]"],
}

NEVER_LOGGED_IN = {"", "never", "1970-01-01t00:00:00.000z"}


@dataclass
class Finding:
    email: str
    issue: str
    detail: str
    severity: str  # HIGH / MEDIUM / LOW


def _get(row: dict, field: str) -> str:
    for name in COLUMN_ALIASES[field]:
        if name in row:
            return (row[name] or "").strip()
    return ""


def _truthy(value: str) -> bool:
    return value.lower() in {"true", "yes", "1", "suspended", "enrolled"}


def _parse_date(value: str) -> datetime | None:
    if value.lower() in NEVER_LOGGED_IN:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def audit(rows: list[dict], inactive_days: int = 90, now: datetime | None = None) -> list[Finding]:
    now = now or datetime.now(timezone.utc)
    findings: list[Finding] = []

    for row in rows:
        email = _get(row, "email")
        if not email:
            continue
        suspended = _truthy(_get(row, "suspended"))
        admin = _truthy(_get(row, "is_admin"))
        has_2sv = _truthy(_get(row, "enrolled_2sv"))
        last_login = _parse_date(_get(row, "last_login"))

        if suspended:
            findings.append(Finding(email, "Suspended account", "Still consumes a licence until deleted or archived", "LOW"))
            continue

        if admin and not has_2sv:
            findings.append(Finding(email, "Admin without 2SV", "Super/delegated admin is not enrolled in 2-Step Verification", "HIGH"))
        elif not has_2sv:
            findings.append(Finding(email, "No 2SV", "User is not enrolled in 2-Step Verification", "MEDIUM"))

        if last_login is None:
            findings.append(Finding(email, "Never signed in", "Account created but never used", "MEDIUM"))
        else:
            days = (now - last_login).days
            if days >= inactive_days:
                findings.append(Finding(email, "Inactive", f"Last sign-in {days} days ago", "MEDIUM"))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(findings, key=lambda f: (order[f.severity], f.email))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_file", help="User export CSV")
    parser.add_argument("--inactive-days", type=int, default=90, help="Days without sign-in to flag (default 90)")
    parser.add_argument("--out", help="Write findings to this CSV instead of printing")
    args = parser.parse_args(argv)

    with open(args.csv_file, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    findings = audit(rows, args.inactive_days)

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["severity", "email", "issue", "detail"])
            for x in findings:
                writer.writerow([x.severity, x.email, x.issue, x.detail])
        print(f"{len(findings)} finding(s) written to {args.out}")
    else:
        print(f"Audited {len(rows)} users, {len(findings)} finding(s)\n")
        for x in findings:
            print(f"[{x.severity:<6}] {x.email:<32} {x.issue}: {x.detail}")

    return 1 if any(x.severity == "HIGH" for x in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
