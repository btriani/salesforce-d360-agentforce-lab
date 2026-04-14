#!/usr/bin/env python3
"""Best-known workflow entrypoint for Health Score segment creation."""

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
    query_rows,
    ssot_api_path,
    workflow_boundary_message,
)

WORKFLOW_NAME = "create_segments"
SEGMENT_ENDPOINT = ssot_api_path("segments")
SEGMENT_DEFINITIONS = {
    "At Risk": lambda score: score < 40,
    "Healthy": lambda score: 40 <= score < 75,
    "Upsell Ready": lambda score: score >= 75,
}


def numeric_score(row: dict[str, object]) -> float:
    """Normalize the readiness query score field for local preview bucketing."""
    value = row["health_score__c"]
    return float(value)


def preview_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    """Preview segment membership from the validated readiness SQL output."""
    counts = {name: 0 for name in SEGMENT_DEFINITIONS}
    for row in rows:
        score = numeric_score(row)
        for name, predicate in SEGMENT_DEFINITIONS.items():
            if predicate(score):
                counts[name] += 1
                break
    return counts


def main() -> None:
    instance, headers = connect()
    _payload, rows = query_rows(instance, headers, HEALTH_SCORE_QUERY_SQL)
    counts = preview_counts(rows)

    raise SystemExit(
        workflow_boundary_message(
            WORKFLOW_NAME,
            endpoint=SEGMENT_ENDPOINT,
            unsupported_step=(
                "segment creation depends on a deployed Health Score calculated insight and an "
                "unvalidated /ssot/segments POST body"
            ),
            detail=(
                "the preview counts come from DLO-backed ad-hoc SQL on "
                "/services/data/v64.0/ssot/queryv2 only; they do not prove DMO-backed "
                "Health Score CI readiness or /services/data/v64.0/ssot/segments readiness"
            ),
            preview_counts=counts,
            query_preview_rows=len(rows),
        )
    )


if __name__ == "__main__":
    main()
