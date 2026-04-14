#!/usr/bin/env python3
"""Best-known workflow entrypoint for Health Score calculated insight creation."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from _common import (
    HEALTH_SCORE_QUERY_SQL,
    connect,
    fetch_custom_dmo_detail,
    query_rows,
    response_status,
    ssot_api_path,
    workflow_boundary_message,
)

WORKFLOW_NAME = "create_health_score_ci"
CI_ENDPOINT = ssot_api_path("calculated-insights")
REQUIRED_EXTERNAL_DMOS = (
    "Web_Engagement",
    "Product_Telemetry",
    "Firmographic_Data",
)


def main() -> None:
    instance, headers = connect()
    _payload, rows = query_rows(instance, headers, HEALTH_SCORE_QUERY_SQL)
    dmo_statuses = {
        name: response_status(fetch_custom_dmo_detail(instance, headers, name).get("response"))
        for name in REQUIRED_EXTERNAL_DMOS
    }
    missing_dmos = [name for name, status_code in dmo_statuses.items() if status_code != 200]

    raise SystemExit(
        workflow_boundary_message(
            WORKFLOW_NAME,
            endpoint=CI_ENDPOINT,
            unsupported_step=(
                "final Health Score calculated insight creation with external data is not "
                "validated in this repo"
            ),
            detail=(
                "the preview comes from DLO-backed ad-hoc SQL on "
                "/services/data/v64.0/ssot/queryv2 using Web_Analytics__dll and product_usage__dll; "
                "it proves DLO queryability only and does not prove DMO-backed "
                "/services/data/v64.0/ssot/calculated-insights readiness"
            ),
            query_preview_rows=len(rows),
            missing_external_dmos=missing_dmos,
        )
    )


if __name__ == "__main__":
    main()
