"""Shared helpers for D360 deployment scripts.

Authentication uses the SF CLI (`sf org display`). Set SF_ORG_ALIAS env var
to switch orgs; defaults to "my-dev-org".
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SF_ORG_ALIAS = os.environ.get("SF_ORG_ALIAS", "my-dev-org")
API_VERSION = "v64.0"
BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR.parent / "artifacts"
SSOT_RELATIVE_PREFIX = f"/services/data/{API_VERSION}/ssot"

HEALTH_SCORE_QUERY_SQL = """
SELECT
    acc.Id__c AS account_id__c,
    acc.Name__c AS account_name__c,
    acc.Industry__c AS industry__c,
    COALESCE(ROUND(AVG(pu.feature_adoption_score__c)), 0) AS product_adoption__c,
    COALESCE(ROUND(LEAST(AVG(wa.page_views_30d__c) / 500, 1) * 50
             + LEAST(AVG(wa.demo_page_visits__c) / 3, 1) * 50), 0) AS web_engagement__c,
    GREATEST(100 - SUM(CASE WHEN c.Status__c != 'Closed' THEN 15 ELSE 0 END)
             - SUM(CASE WHEN c.Status__c = 'Escalated' THEN 25 ELSE 0 END), 0) AS support_health__c,
    COALESCE(ROUND(AVG(CASE WHEN o.StageName__c NOT IN ('Closed Won', 'Closed Lost')
                             THEN o.Probability__c END)), 0) AS deal_momentum__c,
    ROUND(
        COALESCE(AVG(pu.feature_adoption_score__c), 0) * 0.40
        + COALESCE(LEAST(AVG(wa.page_views_30d__c) / 500, 1) * 50 + LEAST(AVG(wa.demo_page_visits__c) / 3, 1) * 50, 0) * 0.20
        + GREATEST(100 - SUM(CASE WHEN c.Status__c != 'Closed' THEN 15 ELSE 0 END) - SUM(CASE WHEN c.Status__c = 'Escalated' THEN 25 ELSE 0 END), 0) * 0.20
        + COALESCE(AVG(CASE WHEN o.StageName__c NOT IN ('Closed Won', 'Closed Lost') THEN o.Probability__c END), 0) * 0.20
    ) AS health_score__c
FROM Account_Home__dll acc
LEFT JOIN Contact_Home__dll cc ON cc.AccountId__c = acc.Id__c
LEFT JOIN Web_Analytics__dll wa ON wa.user_email__c = cc.Email__c
LEFT JOIN product_usage__dll pu ON pu.user_email__c = cc.Email__c
LEFT JOIN Case_Home__dll c ON c.AccountId__c = acc.Id__c
LEFT JOIN Opportunity_Home__dll o ON o.AccountId__c = acc.Id__c
GROUP BY acc.Id__c, acc.Name__c, acc.Industry__c
""".strip()


def get_session():
    """Return (instance_url, access_token) by calling `sf org display`."""
    try:
        result = subprocess.run(
            ["sf", "org", "display", "--target-org", SF_ORG_ALIAS, "--json"],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        print("❌ Salesforce CLI (sf) not found. Install: brew install sf")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ SF CLI failed: {e.stderr}")
        print(f"   Re-authenticate: sf org login web --alias {SF_ORG_ALIAS}")
        sys.exit(1)
    org = json.loads(result.stdout)["result"]
    return org["instanceUrl"], org["accessToken"]


def connect():
    """Return a prepared requests session-like (instance_url, headers)."""
    instance, token = get_session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return instance, headers


def ensure_artifacts_dir():
    """Create and return the shared artifacts directory for this phase."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def evidence_path(prefix):
    """Return a unique JSON artifact path for a probe or verification run."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    safe_prefix = str(prefix).strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    return ensure_artifacts_dir() / f"{safe_prefix}-{timestamp}.json"


def write_evidence(prefix, payload):
    """Write structured evidence JSON and return the file path as a string."""
    path = evidence_path(prefix)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)


def connect_api_url(instance, path):
    """Build a Data Cloud Connect API URL for a relative ssot path."""
    return f"{instance}{ssot_api_path(path)}"


def ssot_query_url(instance):
    """Build the standard Data Cloud query endpoint URL."""
    return connect_api_url(instance, "queryv2")


def ssot_api_path(path: str) -> str:
    """Build the instance-relative path for a Data Cloud Connect API endpoint."""
    return f"{SSOT_RELATIVE_PREFIX}/{str(path).lstrip('/')}"


def ssot_url(instance, path):
    """Build a Data Cloud Connect API URL."""
    return connect_api_url(instance, path)


def resolve_request_url(instance: str, endpoint: str) -> str:
    """Resolve a full request URL from either an absolute or instance-relative endpoint."""
    endpoint = str(endpoint).strip()
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    return f"{instance}{endpoint}"


def response_payload(response: requests.Response) -> Any | None:
    """Return parsed JSON when available, otherwise None."""
    try:
        return response.json()
    except ValueError:
        return None


def response_summary(response: requests.Response, *, body_limit: int = 500) -> dict[str, Any]:
    """Normalize a requests response into a compact evidence-friendly shape."""
    body_text = response.text or ""
    summary = {
        "status_code": response.status_code,
        "ok": response.ok,
        "reason": response.reason,
        "url": response.url,
        "body_preview": body_text[:body_limit],
    }
    payload = response_payload(response)
    if payload is not None:
        summary["body_json"] = payload
    return summary


def request_exception_summary(exc: requests.RequestException) -> dict[str, Any]:
    """Normalize a requests exception for probe evidence."""
    summary = {"error": f"{type(exc).__name__}: {exc}"}
    response = getattr(exc, "response", None)
    if response is not None:
        summary["response"] = response_summary(response)
    return summary


def fetch_ssot(
    instance: str,
    headers: dict[str, str],
    path: str,
    *,
    method: str = "GET",
    json_body: Any | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Call an ssot endpoint and capture either the response or request exception."""
    endpoint = ssot_api_path(path)
    url = f"{instance}{endpoint}"
    result: dict[str, Any] = {
        "endpoint": endpoint,
        "method": method.upper(),
        "url": url,
    }
    try:
        response = requests.request(
            result["method"],
            url,
            headers=headers,
            json=json_body,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        result["error"] = request_exception_summary(exc)
        return result

    result["response"] = response_summary(response)
    return result


def _markdown_replay_blocks(markdown_path: Path) -> list[tuple[str, str]]:
    """Return replay example ids paired with their JSON code-fence bodies."""
    text = markdown_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"<!--\s*replay-example:\s*([A-Za-z0-9_.-]+)\s*-->\s*```json\s*(.*?)\s*```",
        re.DOTALL,
    )
    return [(example_id, payload_text) for example_id, payload_text in pattern.findall(text)]


def list_markdown_replay_examples(markdown_path: Path) -> list[str]:
    """Return replay example ids declared in a markdown notes file."""
    return [example_id for example_id, _payload_text in _markdown_replay_blocks(markdown_path)]


def load_markdown_replay_example(markdown_path: Path, example_id: str) -> Any:
    """Load a JSON replay example declared after a replay-example marker."""
    for candidate_id, payload_text in _markdown_replay_blocks(markdown_path):
        if candidate_id == example_id:
            return json.loads(payload_text)
    raise KeyError(f"Replay example '{example_id}' not found in {markdown_path}")


def custom_dmo_api_name(spec_or_name: dict[str, Any] | str) -> str:
    """Return the custom DMO API name with the __dlm suffix applied once."""
    name = spec_or_name if isinstance(spec_or_name, str) else spec_or_name["name"]
    return name if name.endswith("__dlm") else f"{name}__dlm"


def custom_dmo_detail_url(instance: str, spec_or_name: dict[str, Any] | str) -> str:
    """Build the detail URL for a specific custom DMO."""
    return ssot_url(instance, f"data-model-objects/{custom_dmo_api_name(spec_or_name)}")


def custom_dmo_field_api_name(field_name: str) -> str:
    """Return the custom DMO field API name with the __c suffix applied once."""
    return field_name if field_name.endswith("__c") else f"{field_name}__c"


def fetch_custom_dmo_detail(
    instance: str,
    headers: dict[str, str],
    spec_or_name: dict[str, Any] | str,
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    """Fetch one custom DMO detail response without raising for non-200 statuses."""
    return fetch_ssot(
        instance,
        headers,
        f"data-model-objects/{custom_dmo_api_name(spec_or_name)}",
        timeout=timeout,
    )


def validate_custom_dmo_schema(
    detail_payload: Any,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Validate that an existing DMO matches the required workflow spec."""
    issues: list[str] = []
    missing_fields: list[str] = []
    type_mismatches: list[str] = []
    primary_key_mismatches: list[str] = []

    if not isinstance(detail_payload, dict):
        return {
            "ok": False,
            "issues": ["detail payload missing or not an object"],
            "missing_fields": missing_fields,
            "type_mismatches": type_mismatches,
            "primary_key_mismatches": primary_key_mismatches,
        }

    expected_category = str(spec.get("category", "")).upper()
    actual_category = str(detail_payload.get("category", "")).upper()
    if expected_category and actual_category != expected_category:
        issues.append(f"category expected {expected_category} got {actual_category or 'MISSING'}")

    actual_fields_by_name = {}
    for field in detail_payload.get("fields") or []:
        if isinstance(field, dict) and field.get("name"):
            actual_fields_by_name[str(field["name"])] = field

    for expected_field in spec.get("fields") or []:
        expected_name = custom_dmo_field_api_name(str(expected_field["name"]))
        actual_field = actual_fields_by_name.get(expected_name)
        if actual_field is None:
            missing_fields.append(expected_name)
            continue

        expected_type = str(expected_field.get("dataType", "")).upper()
        actual_type = str(actual_field.get("type", "")).upper()
        if expected_type and actual_type != expected_type:
            type_mismatches.append(f"{expected_name}: expected {expected_type} got {actual_type or 'MISSING'}")

        expected_primary_key = bool(expected_field.get("isPrimaryKey"))
        actual_primary_key = bool(actual_field.get("isPrimaryKey"))
        if expected_primary_key != actual_primary_key:
            primary_key_mismatches.append(
                f"{expected_name}: expected isPrimaryKey={expected_primary_key} got {actual_primary_key}"
            )

    if missing_fields:
        issues.append(f"missing fields {missing_fields}")
    if type_mismatches:
        issues.append(f"type mismatches {type_mismatches}")
    if primary_key_mismatches:
        issues.append(f"primary key mismatches {primary_key_mismatches}")

    return {
        "ok": not issues,
        "issues": issues,
        "missing_fields": missing_fields,
        "type_mismatches": type_mismatches,
        "primary_key_mismatches": primary_key_mismatches,
    }


def custom_dmo_schema_validation_detail(validation: dict[str, Any]) -> str:
    """Summarize a DMO schema validation result into one workflow-safe line."""
    issues = validation.get("issues") or []
    if not issues:
        return "schema matches expected spec"
    return "; ".join(str(issue) for issue in issues)


def create_custom_dmo(
    instance: str,
    headers: dict[str, str],
    spec: dict[str, Any],
    *,
    check_existing: bool = True,
    timeout: int = 60,
) -> dict[str, Any]:
    """Create a custom DMO and return a structured result for workflows and probes."""
    result: dict[str, Any] = {
        "payload": spec,
        "dmo_api_name": custom_dmo_api_name(spec),
        "create_url": ssot_url(instance, "data-model-objects"),
    }

    if check_existing:
        preflight_url = custom_dmo_detail_url(instance, spec)
        result["preflight_url"] = preflight_url
        try:
            preflight = requests.get(preflight_url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            result["preflight"] = request_exception_summary(exc)
            result["ok"] = False
            result["outcome"] = "preflight_error"
            result["message"] = result["preflight"]["error"]
            return result

        result["preflight"] = response_summary(preflight, body_limit=300)
        if preflight.status_code == 200:
            validation = validate_custom_dmo_schema(result["preflight"].get("body_json"), spec)
            result["schema_validation"] = validation
            if validation["ok"]:
                result["ok"] = True
                result["outcome"] = "already_exists"
                result["message"] = "already exists with matching schema"
                return result

            result["ok"] = False
            result["outcome"] = "schema_mismatch"
            result["message"] = custom_dmo_schema_validation_detail(validation)
            return result

    try:
        create_response = requests.post(
            result["create_url"],
            headers=headers,
            json=spec,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        result["create_response"] = request_exception_summary(exc)
        result["ok"] = False
        result["outcome"] = "request_error"
        result["message"] = result["create_response"]["error"]
        return result

    result["create_response"] = response_summary(create_response)
    if create_response.status_code in (200, 201):
        result["ok"] = True
        result["outcome"] = "created"
        result["message"] = f"HTTP {create_response.status_code}"
        return result

    result["ok"] = False
    result["outcome"] = "failed"
    result["message"] = (
        f"HTTP {create_response.status_code}: "
        f"{result['create_response'].get('body_preview', '')}"
    )[:500]
    return result


def response_status(summary: dict[str, Any] | None) -> int | None:
    """Return an HTTP status code from a normalized response summary when present."""
    if not isinstance(summary, dict):
        return None
    value = summary.get("status_code")
    return int(value) if isinstance(value, int) else None


def response_error_code(summary: dict[str, Any] | None) -> str | None:
    """Extract the leading Salesforce errorCode when the body uses the standard list shape."""
    if not isinstance(summary, dict):
        return None
    body_json = summary.get("body_json")
    if isinstance(body_json, list) and body_json and isinstance(body_json[0], dict):
        error_code = body_json[0].get("errorCode")
        if error_code:
            return str(error_code)
    return None


def result_http_status(result: dict[str, Any]) -> int | None:
    """Return the most relevant HTTP status from a workflow result dictionary."""
    for key in ("create_response", "response", "preflight"):
        status_code = response_status(result.get(key))
        if status_code is not None:
            return status_code
    error_response = result.get("error", {}).get("response")
    return response_status(error_response)


def _message_value(value: Any) -> str:
    """Render workflow message values into compact single-line strings."""
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    if isinstance(value, (list, tuple, set)):
        return ",".join(_message_value(item) for item in value)
    return str(value).replace("\n", " ").strip()


def workflow_success_message(
    workflow: str,
    *,
    endpoint: str,
    detail: str,
    **fields: Any,
) -> str:
    """Build a single-line success summary for a workflow script."""
    parts = ["SUCCESS", workflow, f"endpoint={endpoint}", f"detail={_message_value(detail)}"]
    parts.extend(
        f"{key}={_message_value(value)}"
        for key, value in fields.items()
        if value is not None
    )
    return " ".join(parts)


def workflow_boundary_message(
    workflow: str,
    *,
    endpoint: str,
    unsupported_step: str,
    detail: str,
    **fields: Any,
) -> str:
    """Build a single-line explicit boundary message for a workflow script."""
    parts = [
        "BOUNDARY",
        workflow,
        f"endpoint={endpoint}",
        f"unsupported_step={_message_value(unsupported_step)}",
        f"detail={_message_value(detail)}",
    ]
    parts.extend(
        f"{key}={_message_value(value)}"
        for key, value in fields.items()
        if value is not None
    )
    return " ".join(parts)


def query(instance, headers, sql):
    """Run a Data Cloud SQL query and return the parsed response."""
    r = requests.post(
        ssot_query_url(instance),
        headers=headers, json={"sql": sql}, timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Query failed ({r.status_code}): {r.text[:500]}")
    return r.json()


def query_rows(instance, headers, sql):
    """Run a SQL query and normalize the response rows to dictionaries."""
    payload = query(instance, headers, sql)
    rows = payload.get("data") or []
    metadata = payload.get("metadata") or {}
    ordered_columns = sorted(
        metadata.items(),
        key=lambda item: item[1].get("placeInOrder", 0),
    )

    normalized = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(row)
            continue

        if not isinstance(row, (list, tuple)):
            raise RuntimeError(f"Unsupported query row shape: {type(row).__name__}")

        normalized.append(
            {
                column_name: row[index] if index < len(row) else None
                for index, (column_name, _details) in enumerate(ordered_columns)
            }
        )

    return payload, normalized


def first_scalar(row: dict[str, Any]) -> Any:
    """Return the first scalar value from a normalized row."""
    if not row:
        raise RuntimeError("Expected at least one column in query result row.")
    return next(iter(row.values()))
