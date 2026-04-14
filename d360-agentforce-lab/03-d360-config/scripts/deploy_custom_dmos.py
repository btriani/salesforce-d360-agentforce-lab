"""
Attempt custom DMO creation for external data (Web Analytics, Product Usage, Firmographic).

These DMOs mirror the external DLO schemas and are needed because Calculated
Insights can only JOIN DMOs (not DLOs). After creating the DMOs, the DLO data
still needs to be mapped to them (see deploy_dlo_dmo_mappings.py).

This script uses the best-known API surface only. It does not prove that the
endpoint is healthy in the current org, so probe it first before relying on
these requests as a deployment workflow.

The 3 custom DMO specs preserved here:
  - Web_Engagement__dlm       — individual-level web activity
  - Product_Usage__dlm         — individual-level product telemetry
  - Firmographic_Data__dlm     — account-level enrichment
"""
import sys
from _common import SF_ORG_ALIAS, connect, create_custom_dmo, write_evidence

# DMO definitions — mirror the external DLO schemas
DMOS = [
    {
        "name": "Web_Engagement",
        "label": "Web Engagement",
        "category": "Engagement",
        "fields": [
            {"name": "user_email", "label": "User Email", "dataType": "Text", "isPrimaryKey": True},
            {"name": "company_domain", "label": "Company Domain", "dataType": "Text"},
            {"name": "page_views_30d", "label": "Page Views 30d", "dataType": "Number"},
            {"name": "product_pages_viewed", "label": "Product Pages Viewed", "dataType": "Number"},
            {"name": "demo_page_visits", "label": "Demo Page Visits", "dataType": "Number"},
            {"name": "avg_session_minutes", "label": "Avg Session Minutes", "dataType": "Number"},
            {"name": "last_visit_date", "label": "Last Visit Date", "dataType": "Date"},
        ],
    },
    {
        "name": "Product_Telemetry",
        "label": "Product Telemetry",
        "category": "Engagement",
        "fields": [
            {"name": "user_email", "label": "User Email", "dataType": "Text", "isPrimaryKey": True},
            {"name": "company_domain", "label": "Company Domain", "dataType": "Text"},
            {"name": "account_id_external", "label": "External Account Id", "dataType": "Text"},
            {"name": "feature_adoption_score", "label": "Feature Adoption Score", "dataType": "Number"},
            {"name": "api_calls_30d", "label": "API Calls 30d", "dataType": "Number"},
            {"name": "active_users", "label": "Active Users", "dataType": "Number"},
            {"name": "last_login_date", "label": "Last Login Date", "dataType": "Date"},
            {"name": "data_volume_gb", "label": "Data Volume GB", "dataType": "Number"},
        ],
    },
    {
        "name": "Firmographic_Data",
        "label": "Firmographic Data",
        "category": "Profile",
        "fields": [
            {"name": "domain", "label": "Domain", "dataType": "Text", "isPrimaryKey": True},
            {"name": "company_name", "label": "Company Name", "dataType": "Text"},
            {"name": "employee_count", "label": "Employee Count", "dataType": "Number"},
            {"name": "annual_revenue_estimate", "label": "Annual Revenue Estimate", "dataType": "Number"},
            {"name": "funding_stage", "label": "Funding Stage", "dataType": "Text"},
            {"name": "tech_stack_tags", "label": "Tech Stack Tags", "dataType": "Text"},
        ],
    },
]


def status_line(result):
    """Format the most relevant status details from a DMO request result."""
    if result.get("outcome") == "already_exists":
        status = result.get("preflight", {}).get("status_code", "n/a")
        return f"HTTP {status}: already exists"

    create_response = result.get("create_response", {})
    if isinstance(create_response, dict) and create_response.get("status_code") is not None:
        return f"HTTP {create_response['status_code']}: {result.get('outcome')}"

    return str(result.get("message", "request outcome unavailable"))


def main():
    instance, headers = connect()
    print("This script now uses the best-known workflow surface for custom DMO creation.")
    print("Run probe_dmo_field_types.py first if the endpoint behavior is unknown in this org.")
    print()

    any_failed = False
    attempt_summaries = []
    for spec in DMOS:
        result = create_custom_dmo(instance, headers, spec, check_existing=True)
        ok = bool(result.get("ok"))
        marker = "✅" if ok else "❌"
        evidence_payload = {
            "workflow": "deploy_custom_dmos",
            "org_alias": SF_ORG_ALIAS,
            "instance_url": instance,
            "dmo_name": spec["name"],
            "dmo_api_name": result["dmo_api_name"],
            "api_outcome": "success" if ok else "failure",
            "result": result,
        }
        evidence_file = write_evidence(f"deploy_custom_dmo_{spec['name']}", evidence_payload)
        attempt_summaries.append(
            {
                "dmo_name": spec["name"],
                "dmo_api_name": result["dmo_api_name"],
                "api_outcome": "success" if ok else "failure",
                "status_line": status_line(result),
                "evidence_file": evidence_file,
            }
        )
        print(f"  {marker} {result['dmo_api_name']} — {status_line(result)} evidence={evidence_file}")
        if not ok:
            any_failed = True

    summary_file = write_evidence(
        "deploy_custom_dmos_summary",
        {
            "workflow": "deploy_custom_dmos",
            "org_alias": SF_ORG_ALIAS,
            "instance_url": instance,
            "api_surface": "mixed" if any_failed and any(
                item["api_outcome"] == "success" for item in attempt_summaries
            ) else ("failed" if any_failed else "success_or_exists"),
            "results": attempt_summaries,
        },
    )

    print()
    if any_failed:
        print("Some custom DMO requests failed on the current API surface.")
        print("Review the raw probe evidence before treating this workflow as validated.")
        print(f"Deployment summary evidence: {summary_file}")
        sys.exit(1)

    print("All custom DMO requests returned success or already-exists responses.")
    print("This is not proof of downstream mapping, ingestion, or queryability.")
    print(f"Deployment summary evidence: {summary_file}")
    print("Next: confirm probe evidence, then run deploy_dlo_dmo_mappings.py if appropriate.")


if __name__ == "__main__":
    main()
