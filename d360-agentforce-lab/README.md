# D360 + Agentforce Hands-On Lab

An end-to-end Data Cloud (D360) pipeline demonstrating the core value proposition:
**Data + AI + CRM + Trust → Agentforce acts.**

## Scenario

A B2B company has customer data fragmented across CRM and external systems. We unify it in D360, create insights, and build an Agentforce agent that acts on the complete customer view.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                        │
│                                                                             │
│  Salesforce CRM                    Databricks (Delta Lake)                  │
│  ┌──────────────┐                  ┌────────────────────────┐               │
│  │ 25 Accounts  │                  │ Web Analytics (20 rows)│               │
│  │ 62 Contacts  │                  │ Product Usage (25 rows)│               │
│  │ 40 Opps      │                  │ Firmographic   (25 rows│               │
│  │ 18 Cases     │                  │                        │               │
│  └──────┬───────┘                  └───────────┬────────────┘               │
│         │                                      │                            │
│    CRM Native                         Query Federation                      │
│    Ingestion                          (Zero Copy / Live)                    │
│    (free)                                      │                            │
└─────────┼──────────────────────────────────────┼────────────────────────────┘
          │                                      │
          ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SALESFORCE DATA CLOUD (D360)                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  DATA LAKE OBJECTS (DLOs) — Raw data, source schema preserved   │        │
│  │                                                                 │        │
│  │  Account_Home │ Contact_Home │ Opp_Home │ Case_Home             │        │
│  │  Web Analytics│ Product Usage│ Firmographic Enrichment          │        │
│  └────────────────────────────┬────────────────────────────────────┘        │
│                               │ Mapping                                     │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  DATA MODEL OBJECTS (DMOs) — Normalized canonical model         │        │
│  │                                                                 │        │
│  │  Account (std) │ Individual (std) │ Sales Order │ Case (std)    │        │
│  │  Web Analytics (custom) │ Product Usage (custom) │ Firmographic │        │
│  └────────────────────────────┬────────────────────────────────────┘        │
│                               │                                             │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  IDENTITY RESOLUTION                                            │        │
│  │                                                                 │        │
│  │  Contact email (jane@apexfintech.com)                           │        │
│  │       ↕ matches                                                 │        │
│  │  Web analytics domain (apexfintech.com)                         │        │
│  │       ↕ matches                                                 │        │
│  │  Product usage domain (apexfintech.com)                         │        │
│  │       ↕ matches                                                 │        │
│  │  Firmographic company (Apex Financial Technologies)             │        │
│  │                                                                 │        │
│  │  → Unified Profile: One view of the customer                    │        │
│  └────────────────────────────┬────────────────────────────────────┘        │
│                               │                                             │
│              ┌────────────────┼────────────────┐                            │
│              ▼                ▼                 ▼                            │
│  ┌──────────────┐ ┌──────────────────┐ ┌──────────────┐                    │
│  │  CALCULATED   │ │   SEGMENTS       │ │  DATA         │                   │
│  │  INSIGHTS     │ │                  │ │  ACTIONS      │                   │
│  │               │ │  • At Risk       │ │               │                   │
│  │  • Health     │ │  • Upsell Ready  │ │  Activate to  │                   │
│  │    Score      │ │  • Healthy       │ │  Marketing,   │                   │
│  │  • Engagement │ │                  │ │  Sales, Ads   │                   │
│  │    Score      │ │                  │ │               │                   │
│  └──────┬───────┘ └────────┬─────────┘ └──────────────┘                    │
│         │                  │                                                │
│         └──────────┬───────┘                                                │
│                    ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │  AGENTFORCE                                                     │        │
│  │                                                                 │        │
│  │  "Which accounts need attention?"                               │        │
│  │  → Queries At Risk segment + Health Score + unified profile     │        │
│  │  → Recommends next-best-action grounded in ALL data sources     │        │
│  │                                                                 │        │
│  │  Einstein Trust Layer: data access governed by permissions      │        │
│  └─────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## What Each Phase Covers

| Phase | What | D360 Concepts | Status |
|-------|------|---------------|--------|
| [01-synthetic-data](01-synthetic-data/) | Generate & load CRM data via Python + REST API | CRM-native ingestion, data model foundation | Complete |
| [02-external-data](02-external-data/) | Create Delta tables in Databricks via SQL API | External data sources, Zero Copy, Query Federation | Complete |
| [03-d360-config](03-d360-config/) | Connect Databricks, create data streams, map DMOs | Data Streams, DLOs, DMOs, Identity Resolution | Configured |
| [04-agentforce-agent](04-agentforce-agent/) | Design agent grounded in unified D360 data | Agentforce + D360 integration, Trust Layer | Designed |

## Key D360 Concepts Demonstrated

### Data Ingestion
- **CRM Native Ingestion** — Salesforce objects ingested with zero connector cost
- **Query Federation (Zero Copy)** — Databricks Delta tables queried live, no data movement
- **Direct Access (Accelerated)** — Zero Copy with local caching for performance

### Data Modeling
- **Data Lake Objects (DLOs)** — Raw data containers preserving source schema
- **Data Model Objects (DMOs)** — Normalized canonical model for cross-source analysis
- **Profile vs Engagement** — Static attributes vs time-series behavioral data

### Data Unification
- **Identity Resolution** — Matching records across sources (email ↔ domain ↔ company name)
- **Match Rules** — Exact, fuzzy, and normalized matching strategies
- **Unified Profiles** — Single customer view from all data sources

### Data Activation
- **Calculated Insights** — Computed metrics (Health Score) from unified data
- **Segments** — At Risk, Upsell Ready, Healthy groupings
- **Agentforce** — AI agents grounded in the unified, trusted data

## Technical Stack

- **Python** — Data generation (Faker, pandas) and Salesforce REST API (simple_salesforce)
- **Databricks** — Delta tables, SQL Warehouse, REST API for programmatic setup
- **Salesforce** — Data Cloud (D360), Agentforce Studio, SF CLI for OAuth
- **Auth** — SF CLI OAuth (browser flow), Databricks PAT, no SOAP API needed
