#!/usr/bin/env python3
"""Probe the smallest known custom DMO payload against the live org."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent


def find_repo_root(start: Path) -> Path:
    """Find the repo root by locating the shared handoff doc."""
    for candidate in (start, *start.parents):
        if (candidate / "docs" / "HANDOFF.md").exists():
            return candidate
    raise RuntimeError("Could not locate repo root containing docs/HANDOFF.md.")


REPO_ROOT = find_repo_root(SCRIPT_DIR)
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))
for site_packages in (REPO_ROOT / ".venv" / "lib").glob("python*/site-packages"):
    if str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

from _common import SF_ORG_ALIAS, connect, create_custom_dmo, write_evidence

PAYLOAD_TEMPLATE = {
    "name": "Probe_Minimal",
    "label": "Probe Minimal",
    "category": "Profile",
    "fields": [
        {"name": "probe_key", "label": "Probe Key", "dataType": "Text", "isPrimaryKey": True},
    ],
}


def build_probe_payload() -> dict[str, object]:
    """Add a unique suffix so repeated probe runs do not collide."""
    suffix = datetime.now(timezone.utc).strftime("%m%d%H%M%S%f")
    return {
        **PAYLOAD_TEMPLATE,
        "name": f"{PAYLOAD_TEMPLATE['name']}_{suffix}",
        "label": f"{PAYLOAD_TEMPLATE['label']} {suffix}",
    }


def http_status(result: dict[str, object]) -> str:
    """Extract the most relevant HTTP status for display."""
    for key in ("create_response", "preflight"):
        details = result.get(key)
        if isinstance(details, dict) and details.get("status_code") is not None:
            return f"HTTP {details['status_code']}"
    return "HTTP unavailable"


def main() -> None:
    instance, headers = connect()
    payload = build_probe_payload()
    result = create_custom_dmo(instance, headers, payload, check_existing=False)

    evidence = {
        "probe": "create_custom_dmo",
        "case": "minimal_payload",
        "status": "pass" if result.get("ok") else "fail",
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "result": result,
    }
    evidence_file = write_evidence("probe_create_custom_dmo", evidence)
    status = http_status(result)

    if result.get("ok"):
        print(f"PASS minimal_payload {status} evidence={evidence_file}")
        return

    raise SystemExit(
        f"FAIL minimal_payload {status} message={result.get('message', 'unknown error')} "
        f"evidence={evidence_file}"
    )


if __name__ == "__main__":
    main()
