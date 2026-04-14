#!/usr/bin/env python3
"""Best-known workflow entrypoint for external DLO to DMO mapping."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from _common import (
    connect,
    fetch_ssot,
    response_error_code,
    response_status,
    ssot_api_path,
    workflow_boundary_message,
)

WORKFLOW_NAME = "map_external_dlos"
DISCOVERY_PATHS = ("data-model-objects", "data-lake-objects", "data-streams")
BOUNDARY_PATH = "mappings"
BOUNDARY_ENDPOINT = ssot_api_path(BOUNDARY_PATH)


def main() -> None:
    instance, headers = connect()
    discovery_statuses = {
        path: response_status(fetch_ssot(instance, headers, path).get("response"))
        for path in DISCOVERY_PATHS
    }
    boundary_result = fetch_ssot(instance, headers, BOUNDARY_PATH)
    boundary_response = boundary_result.get("response")
    status_code = response_status(boundary_response) or "unavailable"
    error_code = response_error_code(boundary_response) or "unvalidated"

    raise SystemExit(
        workflow_boundary_message(
            WORKFLOW_NAME,
            endpoint=BOUNDARY_ENDPOINT,
            unsupported_step="external DLO to custom DMO field mapping automation",
            detail=f"{BOUNDARY_ENDPOINT} returned HTTP {status_code} {error_code}",
            discovery_statuses=discovery_statuses,
        )
    )


if __name__ == "__main__":
    main()
