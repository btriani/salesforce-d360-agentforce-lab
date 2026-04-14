"""
Deploy custom DMOs for external data (Web Analytics, Product Usage, Firmographic).

These DMOs mirror the external DLO schemas and are needed because Calculated
Insights can only JOIN DMOs (not DLOs). After creating the DMOs, the DLO data
needs to be mapped to them (see deploy_dlo_dmo_mappings.py).

The 3 custom DMOs created:
  - Web_Engagement__dlm       — individual-level web activity
  - Product_Usage__dlm         — individual-level product telemetry
  - Firmographic_Data__dlm     — account-level enrichment
"""
import sys
import requests
from _common import connect, ssot_url

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


def deploy_dmo(instance, headers, spec):
    """Create one custom DMO. Returns (success, message)."""
    dmo_api_name = f"{spec['name']}__dlm"

    # Check if already exists
    r = requests.get(ssot_url(instance, f"data-model-objects/{dmo_api_name}"),
                     headers=headers, timeout=30)
    if r.status_code == 200:
        return True, f"already exists (skipping)"

    # Create
    r = requests.post(ssot_url(instance, "data-model-objects"),
                      headers=headers, json=spec, timeout=60)
    if r.status_code == 201:
        return True, "created"
    return False, f"HTTP {r.status_code}: {r.text[:300]}"


def main():
    instance, headers = connect()
    print("Deploying custom DMOs for external data...\n")

    any_failed = False
    for spec in DMOS:
        ok, msg = deploy_dmo(instance, headers, spec)
        status = "✅" if ok else "❌"
        print(f"  {status} {spec['name']}__dlm — {msg}")
        if not ok:
            any_failed = True

    print()
    if any_failed:
        print("⚠️  Some DMOs failed to deploy. Review errors above.")
        sys.exit(1)
    print("✅ All custom DMOs deployed.")
    print("   Next: run deploy_dlo_dmo_mappings.py to wire DLO fields to these DMOs")


if __name__ == "__main__":
    main()
