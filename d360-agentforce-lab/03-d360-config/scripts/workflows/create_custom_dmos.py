#!/usr/bin/env python3
"""Best-known workflow entrypoint for external custom DMO creation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from _common import (
    create_custom_dmo,
    connect,
    custom_dmo_schema_validation_detail,
    response_error_code,
    response_status,
    ssot_api_path,
    workflow_boundary_message,
    workflow_success_message,
)

WORKFLOW_NAME = "create_custom_dmos"
DMO_CREATE_ENDPOINT = ssot_api_path("data-model-objects")

DMO_SPECS = [
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


def failure_detail(result: dict[str, Any]) -> str:
    """Summarize the first failing DMO request with the live HTTP evidence."""
    if result.get("outcome") == "schema_mismatch":
        validation = result.get("schema_validation") or {}
        return (
            f"{result['dmo_api_name']} already exists but {custom_dmo_schema_validation_detail(validation)}"
        )

    create_response = result.get("create_response")
    status_code = response_status(create_response) or "unavailable"
    error_code = response_error_code(create_response) or result.get("outcome", "unknown")
    return f"{result['dmo_api_name']} returned HTTP {status_code} {error_code}"


def main() -> None:
    instance, headers = connect()
    created_count = 0
    already_exists_count = 0

    for spec in DMO_SPECS:
        result = create_custom_dmo(instance, headers, spec, check_existing=True)
        if not result.get("ok"):
            raise SystemExit(
                workflow_boundary_message(
                    WORKFLOW_NAME,
                    endpoint=DMO_CREATE_ENDPOINT,
                    unsupported_step=(
                        "realistic external custom DMO creation remains unstable on the public "
                        "Connect API in this org"
                    ),
                    detail=failure_detail(result),
                    dmo_api_name=result["dmo_api_name"],
                    org_surface="minimal one-field create works; business DMO create does not",
                )
            )

        if result.get("outcome") == "created":
            created_count += 1
        elif result.get("outcome") == "already_exists":
            already_exists_count += 1

    print(
        workflow_success_message(
            WORKFLOW_NAME,
            endpoint=DMO_CREATE_ENDPOINT,
            detail="all external DMO specs returned created or already_exists",
            created=created_count,
            already_exists=already_exists_count,
            total=len(DMO_SPECS),
        )
    )


if __name__ == "__main__":
    main()
