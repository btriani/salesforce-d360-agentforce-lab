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
    return f"{instance}/services/data/{API_VERSION}/ssot/{str(path).lstrip('/')}"


def ssot_query_url(instance):
    """Build the standard Data Cloud query endpoint URL."""
    return connect_api_url(instance, "queryv2")


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
            result["ok"] = True
            result["outcome"] = "already_exists"
            result["message"] = "already exists"
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
