"""Shared helpers for D360 deployment scripts.

Authentication uses the SF CLI (`sf org display`). Set SF_ORG_ALIAS env var
to switch orgs; defaults to "my-dev-org".
"""
import json
import os
import subprocess
import sys
import requests

SF_ORG_ALIAS = os.environ.get("SF_ORG_ALIAS", "my-dev-org")
API_VERSION = "v64.0"


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


def ssot_url(instance, path):
    """Build a Data Cloud Connect API URL."""
    return f"{instance}/services/data/{API_VERSION}/ssot/{path}"


def query(instance, headers, sql):
    """Run a Data Cloud SQL query and return the parsed response."""
    r = requests.post(
        f"{instance}/services/data/{API_VERSION}/ssot/queryv2",
        headers=headers, json={"sql": sql}, timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Query failed ({r.status_code}): {r.text[:500]}")
    return r.json()
