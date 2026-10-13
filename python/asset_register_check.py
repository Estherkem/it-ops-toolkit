"""Validate an IT asset register CSV and summarise it.

Checks each row for:
  - missing serial numbers or assignees
  - duplicate serial numbers
  - warranties that have expired or expire within N days
  - devices older than the refresh cycle

Also prints a cost summary by category. If a price is marked as VAT-inclusive
(`price_includes_vat` = yes), the net price is backed out at the given VAT rate.

Expected columns (extra columns are ignored):
    asset_tag, category, model, serial, assigned_to, purchase_date,
    warranty_end, price, price_includes_vat

Usage:
    python asset_register_check.py ../samples/assets.csv
    python asset_register_check.py assets.csv --warranty-days 30 --refresh-years 4 --vat 20
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import date


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for sep in ("-", "/"):
        parts = value.split(sep)
        if len(parts) == 3:
            try:
                if len(parts[0]) == 4:  # YYYY-MM-DD
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
                return date(int(parts[2]), int(parts[1]), int(parts[0]))  # DD/MM/YYYY
            except ValueError:
                return None
    return None


def net_price(row: dict, vat_rate: float) -> float:
    try:
        price = float((row.get("price") or "0").replace(",", "").replace("£", ""))
    except ValueError:
        return 0.0
    if (row.get("price_includes_vat") or "").strip().lower() in {"yes", "y", "true"}:
        price = price / (1 + vat_rate / 100)
    return round(price, 2)


def check(rows: list[dict], today: date, warranty_days: int = 60,
          refresh_years: int = 4, vat_rate: float = 20.0) -> tuple[list[str], dict[str, float]]:
    issues: list[str] = []
    serials = Counter((r.get("serial") or "").strip().upper() for r in rows)
    costs: dict[str, float] = defaultdict(float)

    for r in rows:
        tag = r.get("asset_tag") or "(no tag)"
        serial = (r.get("serial") or "").strip().upper()

        if not serial:
            issues.append(f"{tag}: missing serial number")
        elif serials[serial] > 1:
            issues.append(f"{tag}: duplicate serial {serial}")

        if not (r.get("assigned_to") or "").strip():
            issues.append(f"{tag}: not assigned to anyone (spare or lost?)")

        warranty = parse_date(r.get("warranty_end", ""))
        if warranty:
            days_left = (warranty - today).days
            if days_left < 0:
                issues.append(f"{tag}: warranty expired {-days_left} days ago")
            elif days_left <= warranty_days:
                issues.append(f"{tag}: warranty expires in {days_left} days")

        bought = parse_date(r.get("purchase_date", ""))
        if bought and (today - bought).days > refresh_years * 365:
            issues.append(f"{tag}: older than {refresh_years}-year refresh cycle (bought {bought})")

        costs[(r.get("category") or "Uncategorised").strip()] += net_price(r, vat_rate)

    return issues, dict(costs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_file")
    parser.add_argument("--warranty-days", type=int, default=60)
    parser.add_argument("--refresh-years", type=int, default=4)
    parser.add_argument("--vat", type=float, default=20.0, help="VAT rate %% to back out (default 20)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # so £ prints correctly on Windows consoles

    with open(args.csv_file, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    issues, costs = check(rows, date.today(), args.warranty_days, args.refresh_years, args.vat)

    print(f"{len(rows)} assets checked, {len(issues)} issue(s)\n")
    for line in issues:
        print(f"  - {line}")

    print("\nNet cost by category (ex VAT):")
    for category, total in sorted(costs.items(), key=lambda kv: -kv[1]):
        print(f"  {category:<20} £{total:>10,.2f}")
    print(f"  {'TOTAL':<20} £{sum(costs.values()):>10,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
