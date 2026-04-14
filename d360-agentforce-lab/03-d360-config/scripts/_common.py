"""Shared helpers for D360 deployment scripts.

Authentication uses the SF CLI (`sf org display`). Set SF_ORG_ALIAS env var
to switch orgs; defaults to "my-dev-org".
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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


def query(instance, headers, sql):
    """Run a Data Cloud SQL query and return the parsed response."""
    r = requests.post(
        ssot_query_url(instance),
        headers=headers, json={"sql": sql}, timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Query failed ({r.status_code}): {r.text[:500]}")
    return r.json()
