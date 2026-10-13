# IT Ops Toolkit

Practical scripts for day-to-day IT operations in a small-to-mid-sized company: asset tracking, Google Workspace security hygiene and quick network troubleshooting.

Built from real IT support work. All sample data is fictional.

## What's inside

| Script | Language | What it does |
|---|---|---|
| [`Get-SystemInventory.ps1`](powershell/Get-SystemInventory.ps1) | PowerShell | Collects a laptop's model, serial, CPU, RAM, disks and OS, and exports to CSV/JSON for an asset register |
| [`Test-NetworkHealth.ps1`](powershell/Test-NetworkHealth.ps1) | PowerShell | Checks DNS, ping and TCP ports for a list of hosts. A good first step for "the internet is down" tickets |
| [`workspace_user_audit.py`](python/workspace_user_audit.py) | Python | Audits a Google Workspace user export for admins without 2SV, users without 2SV, inactive accounts and suspended licences |
| [`asset_register_check.py`](python/asset_register_check.py) | Python | Validates an asset register for missing or duplicate serials, unassigned kit, expiring warranties and devices past refresh, plus a cost summary ex-VAT |

The Python scripts only need the standard library (Python 3.9+). No installs required.

## Quick start

```powershell
# Inventory this machine and append it to a CSV
.\powershell\Get-SystemInventory.ps1 -OutFile .\inventory.csv

# Check connectivity
.\powershell\Test-NetworkHealth.ps1 -Targets 'google.com:443','8.8.8.8'
```

```bash
cd python

# Google Workspace audit (export users with GAM or the Admin console)
python workspace_user_audit.py ../samples/users.csv --inactive-days 90

# Asset register health check
python asset_register_check.py ../samples/assets.csv --warranty-days 60
```

### Example output

```
Audited 6 users, 6 finding(s)

[HIGH  ] alex.admin@example.com           Admin without 2SV: Super/delegated admin is not enrolled in 2-Step Verification
[MEDIUM] chris.no2sv@example.com          No 2SV: User is not enrolled in 2-Step Verification
[MEDIUM] dana.leaver@example.com          Inactive: Last sign-in 224 days ago
...
```

`workspace_user_audit.py` exits with code 1 if any HIGH findings exist, so you can run it on a schedule and alert on failure.

### Getting a user export with GAM

```bash
gam print users fields primaryEmail,suspended,isAdmin,isEnrolledIn2Sv,lastLoginTime > users.csv
```

## Running tests

```bash
cd python
python -m pytest tests
```

## Roadmap

- [ ] Onboarding/offboarding checklist generator
- [ ] Shared drive and external-sharing audit
- [ ] Windows update and BitLocker compliance check
- [ ] Scheduled run with Slack/email alerts

## Licence

MIT
