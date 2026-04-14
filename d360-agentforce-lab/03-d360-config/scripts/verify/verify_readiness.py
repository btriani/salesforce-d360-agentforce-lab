#!/usr/bin/env python3
"""Readiness checks to run before any Phase 3 DMO deployment work."""

from __future__ import annotations

import json
import sys
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

from _common import SF_ORG_ALIAS, connect, first_scalar, query_rows, write_evidence

EXPECTED_DMO_QUERIES = {
    "individuals": "SELECT COUNT(*) AS row_count FROM ssot__Individual__dlm",
    "contact_point_email": "SELECT COUNT(*) AS row_count FROM ssot__ContactPointEmail__dlm",
    "accounts": "SELECT COUNT(*) AS row_count FROM ssot__Account__dlm",
    "cases": "SELECT COUNT(*) AS row_count FROM ssot__Case__dlm",
    "sales_orders": "SELECT COUNT(*) AS row_count FROM ssot__SalesOrder__dlm",
}

HEALTH_SCORE_SQL = """
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


def run_count_checks(instance, headers):
    counts = {}
    for label, sql in EXPECTED_DMO_QUERIES.items():
        _payload, rows = query_rows(instance, headers, sql)
        if len(rows) != 1:
            raise RuntimeError(f"{label} count query returned {len(rows)} rows, expected 1.")
        counts[label] = int(first_scalar(rows[0]))
    return counts


def run_health_score_check(instance, headers):
    payload, rows = query_rows(instance, headers, HEALTH_SCORE_SQL)
    if len(rows) < 25:
        raise RuntimeError(
            f"Health Score readiness query returned {len(rows)} account rows; expected at least 25."
        )
    return payload, rows


def main():
    instance, headers = connect()
    counts = run_count_checks(instance, headers)
    health_payload, health_rows = run_health_score_check(instance, headers)

    evidence = {
        "verification": "readiness",
        "status": "pass",
        "org_alias": SF_ORG_ALIAS,
        "instance_url": instance,
        "dmo_counts": counts,
        "readiness_health_score_query_check": {
            "purpose": "proof_of_queryability",
            "interpretation": (
                "This runs the exact Health Score SQL from docs/HANDOFF.md as a readiness check "
                "to prove the ad-hoc query surface is accessible and returns account rows. "
                "These aggregates are not asserted here as a validated final scoring computation."
            ),
            "sql": HEALTH_SCORE_SQL,
            "query_id": health_payload.get("queryId"),
            "row_count": len(health_rows),
            "sample_rows": health_rows[:5],
        },
    }
    evidence_file = write_evidence("readiness", evidence)

    print(
        "PASS readiness "
        f"org={SF_ORG_ALIAS} "
        f"counts={json.dumps(counts, sort_keys=True)} "
        f"health_score_queryability_rows={len(health_rows)} "
        f"evidence={evidence_file}"
    )


if __name__ == "__main__":
    main()
