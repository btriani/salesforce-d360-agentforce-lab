# D360 Lab — Handoff Document

**Date:** 2026-04-14
**Status:** Phase 3 partially complete, blocked on code-first Calculated Insight with cross-source data

## Current State

### What Works ✅

**Phase 1 — CRM Data Generation (COMPLETE)**
- `d360-agentforce-lab/01-synthetic-data/generate_and_load.py` — generates 25 Accounts, 64 Contacts, 39 Opportunities, 18 Cases, loads them into Salesforce via REST API
- Exports `company_reference.json` + `contact_reference.json`
- Fully automated, tested end-to-end

**Phase 2 — External Data Generation (COMPLETE)**
- `d360-agentforce-lab/02-external-data/generate_external_data.py` — generates individual-level Web Analytics (50 rows), Product Usage (44 rows), Firmographic (25 rows)
- `databricks_create_delta_tables.py` — Databricks notebook for Delta table creation
- Fully automated, tested end-to-end

**Phase 3 — D360 Configuration (PARTIAL)**
- 7 Data Streams active in D360:
  - 4 CRM streams (Account_Home, Contact_Home, Opportunity_Home, Case_Home) — auto-ingested
  - 3 Databricks streams (Web_Analytics, product_usage, Firmographic_Enrichment) — all fields imported this time
- CRM Contact DLO mapped to Individual + Contact Point Email DMOs (via UI)
- All CRM DMOs populated: `ssot__Individual__dlm` (64), `ssot__ContactPointEmail__dlm` (64), `ssot__Account__dlm` (26), `ssot__Case__dlm` (18), `ssot__SalesOrder__dlm` (39)
- Cross-source SQL JOIN query works when run ad-hoc via `/ssot/queryv2` (CRM DMOs + external DLOs)
- Calculated Insight creation API works with CRM-only DMOs (confirmed with test CI)

### What Doesn't Work ❌

**Blocker: Calculated Insights with external data**

The goal was a Health Score Calculated Insight that combines CRM data (Account, Case, Sales Order, Individual) with external Databricks data (Web Analytics, Product Usage, Firmographic).

**The core constraint:** Calculated Insight SQL can only reference DMOs (ssot__*__dlm), not DLOs directly. The query engine error:
```
FullColumnName product_usage__dll.feature_adoption_score__c cannot be found
in dependencies or existing DMOs
```

**To bridge this:** The 3 external DLOs must be mapped to custom DMOs. Two paths were attempted:

1. **UI-based mapping (2-day wall):** The mapping UI doesn't reliably expose Contact Point Email as a target DMO for external DLOs in Dev Edition orgs. Dropdown searches return empty results.

2. **API-based custom DMO creation:** `POST /services/data/v64.0/ssot/data-model-objects` works for simple test DMOs but returns HTTP 500 "UNKNOWN_EXCEPTION" when creating DMOs with realistic schemas (7+ fields including Number and Date types):
   ```
   [{"message":"An unexpected error occurred. Please include this ErrorId...","errorCode":"UNKNOWN_EXCEPTION"}]
   ```

**What we know about the API:**
- Field format requires `name`, `label`, `category`, and `fields` array
- Each field needs `name`, `label`, `dataType`, optional `isPrimaryKey`
- Minimal DMO (1 text field) works
- Realistic DMO (multiple fields with various types) returns 500

### Also Discovered

**Identity Resolution cannot be deployed via Metadata API at all** — it's only available via the Connect REST API (`/ssot/identity-resolutions`). We didn't get to building the IR ruleset because we couldn't get past the DMO mapping step.

**Data stream field selection is critical:** When creating external data streams via UI, every field must be individually checked. The default selection includes only Primary Key and Event Time Field, which causes downstream issues. We recreated all 3 external streams to fix this.

## What Was Tried

| Approach | Result |
|----------|--------|
| UI-based Contact Point Email mapping for external DLOs | Silent failures — dropdown empty, match rule created nothing |
| Python deploy script calling `/ssot/identity-resolutions` POST | Schema discovery failed — no documented request body format |
| Python create Calculated Insight via `/ssot/calculated-insights` POST | Works with CRM DMOs only; can't JOIN external DLOs |
| Python create custom DMO via `/ssot/data-model-objects` POST | Works minimally, fails with realistic schemas (HTTP 500) |
| SFDX metadata deployment of DMOs | Not attempted — research indicated mixed support |

## Project Structure

```
bruno-data-ai-labs/
├── README.md                                   # Lab overview with Mermaid diagrams
├── d360-agentforce-lab/
│   ├── README.md                               # Phase summary
│   ├── 01-synthetic-data/
│   │   ├── generate_and_load.py                # ✅ WORKS
│   │   ├── README.md
│   │   ├── company_reference.json              # Generated output
│   │   └── contact_reference.json              # Generated output
│   ├── 02-external-data/
│   │   ├── generate_external_data.py           # ✅ WORKS
│   │   ├── databricks_create_delta_tables.py   # ✅ WORKS
│   │   ├── README.md
│   │   └── csv_exports/                        # Generated CSVs
│   ├── 03-d360-config/
│   │   ├── README.md                           # Step-by-step guide (UI-based, written before pivots)
│   │   └── scripts/                            # ❌ BLOCKED
│   │       ├── _common.py                      # SF CLI auth helper
│   │       ├── deploy_custom_dmos.py           # Fails with HTTP 500
│   │       └── requirements.txt
│   └── 04-agentforce-agent/
│       └── README.md                           # Agent design (not yet deployed)
├── docs/
│   ├── superpowers/
│   │   ├── specs/
│   │   │   ├── 2026-04-14-d360-lab-rewrite-design.md
│   │   │   └── 2026-04-14-phase3-code-first-addendum.md
│   │   └── plans/
│   │       └── 2026-04-14-d360-lab-rewrite.md
│   └── HANDOFF.md                              # This file
└── ...
```

## Environment Details

- **Salesforce Org:** Developer Edition with Data Cloud enabled
  - Username: `btriani.775656397e80@agentforce.com`
  - Instance: `orgfarm-ae1d59d1bd-dev-ed.develop.my.salesforce.com`
  - Auth via SF CLI alias `my-dev-org`
- **Databricks:** Trial workspace
  - Host: `dbc-3cd549f9-402b.cloud.databricks.com` (in `.env`)
  - Warehouse: `dbc63533d8190bea` (Serverless Starter)
  - Catalog/schema: `workspace.d360_lab`
- **Python:** 3.14 in `.venv/` at repo root
- **Dependencies:** `simple_salesforce`, `faker`, `pandas`, `requests`

## Health Score SQL (Target Design)

This SQL was proven to work via `/ssot/queryv2` ad-hoc. The goal is to embed it in a Calculated Insight:

```sql
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
```

When run via `/ssot/queryv2`, this returns all 25 accounts with computed scores ranging 18–77.

## Expected Segments

Once Health Score CI works:
- **At Risk:** health_score < 40 (~5-7 accounts)
- **Healthy:** health_score 40–74 (~16 accounts)
- **Upsell Ready:** health_score ≥ 75 (~1-3 accounts, may need criteria loosening)

## Remaining Work

1. **Create 3 custom DMOs** that mirror the external DLOs (Web_Engagement, Product_Telemetry, Firmographic_Data)
2. **Map DLO fields to DMO fields** — use MktDataLakeMapping SObject? SFDX metadata? UI?
3. **Wait for data to propagate** from DLO to DMO
4. **Create Calculated Insight** using the Health Score SQL, adjusted to reference DMOs instead of DLOs
5. **Create 3 Segments** (At Risk / Healthy / Upsell Ready) via `/ssot/segments` POST
6. **Build Agentforce agent** (Phase 4) grounded in the Health Score CI + Segments
