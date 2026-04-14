#!/usr/bin/env python3
"""Probe custom DMO field-type combinations and record every outcome."""

from __future__ import annotations

import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

BASE_FIELDS = [
    {"name": "probe_key", "label": "Probe Key", "dataType": "Text", "isPrimaryKey": True},
    {"name": "probe_text", "label": "Probe Text", "dataType": "Text"},
]

FIELD_MATRIX = [
    {
        "case": "text_only",
        "description": "Minimal multi-field payload with only text fields.",
        "add_fields": [],
    },
    {
        "case": "with_number",
        "description": "Add one Number field on top of the accepted-or-failing text-only base.",
        "add_fields": [
            {"name": "probe_number", "label": "Probe Number", "dataType": "Number"},
        ],
    },
    {
        "case": "with_date",
        "description": "Add one Date field after the Number expansion to keep the matrix incremental.",
        "add_fields": [
            {"name": "probe_date", "label": "Probe Date", "dataType": "Date"},
        ],
    },
]


def build_probe_payload(case_name: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a unique DMO payload for one matrix case."""
    suffix = datetime.now(timezone.utc).strftime("%m%d%H%M%S%f")
    return {
        "name": f"Probe_{case_name}_{suffix}",
        "label": f"Probe {case_name} {suffix}",
        "category": "Profile",
        "fields": deepcopy(fields),
    }


def http_status(result: dict[str, Any]) -> str:
    """Extract the most relevant HTTP status for display."""
    for key in ("create_response", "preflight"):
        details = result.get(key)
        if isinstance(details, dict) and details.get("status_code") is not None:
            return f"HTTP {details['status_code']}"
    return "REQUEST_ERROR"


def api_outcome_label(result: dict[str, Any]) -> str:
    """Normalize API behavior into a short label."""
    if result.get("ok"):
        return "success"
    if result.get("outcome") == "script_error":
        return "script_error"
    return "failure"


def build_case_fields(matrix_index: int) -> list[dict[str, Any]]:
    """Build cumulative fields so each matrix case expands the prior payload."""
    fields = deepcopy(BASE_FIELDS)
    for case in FIELD_MATRIX[: matrix_index + 1]:
        fields.extend(deepcopy(case["add_fields"]))
    return fields


def summarize_api_outcomes(results: list[dict[str, Any]]) -> str:
    """Describe the underlying API surface independent of probe completeness."""
    api_outcomes = {result["api_outcome"] for result in results}
    if api_outcomes == {"success"}:
        return "all_succeeded"
    if api_outcomes == {"failure"}:
        return "all_failed"
    if "script_error" in api_outcomes:
        return "script_errors_present"
    return "mixed"


def run_case(
    instance: str,
    headers: dict[str, str],
    matrix_index: int,
    case_definition: dict[str, Any],
    prior_case_name: str | None,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run one matrix case and persist its evidence regardless of outcome."""
    case_name = case_definition["case"]
    payload = build_probe_payload(case_name, fields)

    try:
        result = create_custom_dmo(instance, headers, payload, check_existing=False)
    except Exception as exc:  # pragma: no cover - defensive evidence capture
        result = {
            "ok": False,
            "outcome": "script_error",
            "message": f"{type(exc).__name__}: {exc}",
            "payload": payload,
        }

    evidence = {
        "probe": "dmo_field_types",
        "case": case_name,
        "execution_status": "recorded",
        "api_outcome": api_outcome_label(result),
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "investigation": {
            "matrix_index": matrix_index + 1,
            "description": case_definition["description"],
            "prior_case": prior_case_name,
            "base_fields": BASE_FIELDS,
            "cumulative_field_count": len(fields),
            "field_names": [field["name"] for field in fields],
        },
        "result": result,
    }
    evidence_file = write_evidence(f"probe_dmo_field_types_{case_name}", evidence)

    return {
        "case": case_name,
        "execution_status": "recorded",
        "api_outcome": api_outcome_label(result),
        "http_status": http_status(result),
        "message": result.get("message"),
        "evidence_file": evidence_file,
        "dmo_api_name": result.get("dmo_api_name"),
        "field_count": len(fields),
        "prior_case": prior_case_name,
    }


def main() -> None:
    instance, headers = connect()

    results = []
    for matrix_index, case_definition in enumerate(FIELD_MATRIX):
        fields = build_case_fields(matrix_index)
        prior_case_name = None if matrix_index == 0 else FIELD_MATRIX[matrix_index - 1]["case"]
        case_result = run_case(instance, headers, matrix_index, case_definition, prior_case_name, fields)
        results.append(case_result)
        print(
            f"{case_result['case']}: {case_result['http_status']} "
            f"api_outcome={case_result['api_outcome']} "
            f"field_count={case_result['field_count']} "
            f"evidence={case_result['evidence_file']}"
        )

    execution_complete = len(results) == len(FIELD_MATRIX)
    api_status = summarize_api_outcomes(results)

    summary = {
        "probe": "dmo_field_types",
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "execution": {
            "status": "complete" if execution_complete else "incomplete",
            "recorded_case_count": len(results),
            "expected_case_count": len(FIELD_MATRIX),
            "all_cases_recorded": execution_complete,
        },
        "api_surface": {
            "status": api_status,
            "successful_case_count": sum(1 for result in results if result["api_outcome"] == "success"),
            "failed_case_count": sum(1 for result in results if result["api_outcome"] == "failure"),
            "script_error_case_count": sum(
                1 for result in results if result["api_outcome"] == "script_error"
            ),
        },
        "results": results,
    }
    summary_file = write_evidence("probe_dmo_field_types_summary", summary)

    if not execution_complete:
        raise SystemExit(
            f"FAIL matrix_incomplete recorded={len(results)} expected={len(FIELD_MATRIX)} "
            f"summary={summary_file}"
        )

    print(
        f"COMPLETE matrix_recorded cases={len(results)} api_status={api_status} "
        f"summary={summary_file}"
    )


if __name__ == "__main__":
    main()
