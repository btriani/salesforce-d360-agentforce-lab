#!/usr/bin/env python3
"""Inventory candidate mapping-related API paths and preserve every response."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

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

from _common import (
    SF_ORG_ALIAS,
    connect,
    request_exception_summary,
    response_summary,
    ssot_url,
    write_evidence,
)

CANDIDATE_PATHS = [
    "data-model-objects",
    "data-lake-objects",
    "data-mappings",
    "mappings",
    "data-streams",
]


def surface_status(result: dict[str, Any]) -> str:
    """Collapse each probe result into a short investigation label."""
    if result.get("error_type") == "request_exception":
        return "request_error"
    if result.get("error_type") == "script_error":
        return "script_error"
    status_code = result["response"]["status_code"]
    if status_code == 404:
        return "not_found"
    return "observed"


def summarize_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count each outcome bucket for the final summary."""
    buckets = {"observed": 0, "not_found": 0, "request_error": 0, "script_error": 0}
    for result in results:
        buckets[result["surface_status"]] += 1
    return buckets


def execution_status(results: list[dict[str, Any]]) -> str:
    """Describe whether the probe completed its own recording obligations."""
    recorded_paths = {result["path"] for result in results}
    if len(results) != len(CANDIDATE_PATHS) or recorded_paths != set(CANDIDATE_PATHS):
        return "incomplete"
    return "complete"


def api_surface_quality(counts: dict[str, int]) -> str:
    """Describe the quality of the observed API surface independent of execution."""
    if counts["request_error"] or counts["script_error"]:
        return "degraded"
    return "healthy"


def overall_status(execution: str, quality: str) -> str:
    """Summarize execution completeness and API quality in one evidence label."""
    if execution != "complete":
        return execution
    if quality != "healthy":
        return f"{execution}_{quality}"
    return "complete_healthy"


def probe_candidate(instance: str, headers: dict[str, str], path: str) -> dict[str, Any]:
    """Probe one candidate path without treating non-200 responses as failures."""
    url = ssot_url(instance, path)
    result: dict[str, Any] = {
        "path": path,
        "method": "GET",
        "url": url,
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        result["response"] = response_summary(response, body_limit=300)
    except requests.RequestException as exc:
        result["error_type"] = "request_exception"
        result["error"] = request_exception_summary(exc)
    except Exception as exc:  # pragma: no cover - defensive evidence capture
        result["error_type"] = "script_error"
        result["error"] = {"error": f"{type(exc).__name__}: {exc}"}

    result["surface_status"] = surface_status(result)
    return result


def result_status_line(result: dict[str, Any]) -> str:
    """Format one terminal line per candidate for quick scanning."""
    response = result.get("response") or {}
    if response.get("status_code") is not None:
        return (
            f"{result['path']}: HTTP {response['status_code']} "
            f"surface_status={result['surface_status']}"
        )
    return (
        f"{result['path']}: {result['surface_status']} "
        f"error={result.get('error', {}).get('error', 'unknown error')}"
    )


def main() -> None:
    instance, headers = connect()

    results = [probe_candidate(instance, headers, path) for path in CANDIDATE_PATHS]
    counts = summarize_counts(results)
    execution = execution_status(results)
    quality = api_surface_quality(counts)

    evidence = {
        "probe": "mapping_surfaces",
        "status": overall_status(execution, quality),
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "execution": {
            "status": execution,
            "expected_candidate_count": len(CANDIDATE_PATHS),
            "recorded_candidate_count": len(results),
            "all_candidates_recorded": len(results) == len(CANDIDATE_PATHS),
        },
        "api_surface": {
            "quality": quality,
            **counts,
        },
        "results": results,
    }
    evidence_file = write_evidence("probe_mapping_surfaces_summary", evidence)

    for result in results:
        print(result_status_line(result))

    if execution == "incomplete":
        raise SystemExit(
            "FAIL mapping_surfaces "
            f"recorded={len(results)} expected={len(CANDIDATE_PATHS)} "
            f"evidence={evidence_file}"
        )

    summary_prefix = "COMPLETE" if quality == "healthy" else "COMPLETE_WITH_DEGRADED_SURFACE"
    print(
        f"{summary_prefix} mapping_surfaces "
        f"execution={execution} "
        f"api_surface={quality} "
        f"recorded={len(results)} "
        f"observed={counts['observed']} "
        f"not_found={counts['not_found']} "
        f"request_errors={counts['request_error']} "
        f"script_errors={counts['script_error']} "
        f"evidence={evidence_file}"
    )


if __name__ == "__main__":
    main()
