# D360 + Agentforce Hands-On Lab

An end-to-end Data Cloud (D360) pipeline demonstrating the core value proposition:
**Data + AI + CRM + Trust -> Agentforce acts.**

## Scenario

A B2B company has customer data fragmented across CRM and external systems. We unify it in D360 at the **individual level**, create insights, and build an Agentforce agent that acts on the complete customer view.

## Architecture

```
+---------------------------------------------------------------------------+
|                        DATA SOURCES                                       |
|                                                                           |
|  Salesforce CRM                    Databricks (Delta Lake)                |
|  +----------------+               +------------------------------+       |
|  | 25 Accounts    |               | Web Analytics  (~44 rows)    |       |
|  | ~55 Contacts   |               |   keyed by user_email        |       |
|  | ~35 Opps       |               | Product Usage  (~38 rows)    |       |
|  | 18 Cases       |               |   keyed by user_email        |       |
|  +-------+--------+               | Firmographic   (25 rows)     |       |
|          |                         |   keyed by domain            |       |
|     CRM Native                     +-------------+----------------+       |
|     Ingestion                                    |                        |
|     (free)                              Query Federation                  |
|          |                           (Zero Copy / Live)                   |
+----------+-------------------------------+-----------------------------+--+
           |                               |
           v                               v
+---------------------------------------------------------------------------+
|                    SALESFORCE DATA CLOUD (D360)                            |
|                                                                           |
|  +-------------------------------------------------------------------+   |
|  |  DATA LAKE OBJECTS (DLOs) -- Raw data, source schema preserved     |   |
|  |                                                                    |   |
|  |  Account_Home | Contact_Home | Opp_Home | Case_Home               |   |
|  |  Web Analytics | Product Usage | Firmographic Enrichment          |   |
|  +-----------------------------+--------------------------------------+   |
|                                | Mapping                                  |
|                                v                                          |
|  +-------------------------------------------------------------------+   |
|  |  DATA MODEL OBJECTS (DMOs) -- Normalized canonical model           |   |
|  |                                                                    |   |
|  |  Account (std) | Individual (std) | Sales Order | Case (std)      |   |
|  |  Web Analytics (custom) | Product Usage (custom) | Firmographic   |   |
|  +-----------------------------+--------------------------------------+   |
|                                |                                          |
|                                v                                          |
|  +-------------------------------------------------------------------+   |
|  |  IDENTITY RESOLUTION                                               |   |
|  |                                                                    |   |
|  |  Contact Point Email: jane.doe@apexfintech.com                     |   |
|  |       = exact match =                                              |   |
|  |  Web Analytics user_email: jane.doe@apexfintech.com                |   |
|  |       = exact match =                                              |   |
|  |  Product Usage user_email: jane.doe@apexfintech.com                |   |
|  |                                                                    |   |
|  |  -> Unified Individual: one view of jane.doe across 3 sources      |   |
|  +-----------------------------+--------------------------------------+   |
|                                |                                          |
|               +----------------+----------------+                         |
|               v                v                 v                        |
|  +--------------+  +------------------+  +--------------+                 |
|  |  CALCULATED   |  |   SEGMENTS       |  |  DATA        |                |
|  |  INSIGHTS     |  |                  |  |  ACTIONS     |                |
|  |               |  |  - At Risk       |  |              |                |
|  |  - Health     |  |  - Upsell Ready  |  |  Activate to |                |
|  |    Score      |  |  - Healthy       |  |  Marketing,  |                |
|  |               |  |                  |  |  Sales, Ads  |                |
|  +------+-------+  +--------+---------+  +--------------+                |
|         |                   |                                             |
|         +---------+---------+                                             |
|                   v                                                       |
|  +-------------------------------------------------------------------+   |
|  |  AGENTFORCE                                                        |   |
|  |                                                                    |   |
|  |  "Which contacts need attention?"                                  |   |
|  |  -> Queries At Risk segment + Health Score + unified individual    |   |
|  |  -> Recommends next-best-action grounded in ALL data sources      |   |
|  |                                                                    |   |
|  |  Einstein Trust Layer: data access governed by permissions         |   |
|  +-------------------------------------------------------------------+   |
+---------------------------------------------------------------------------+
```

## What Each Phase Covers

| Phase | What | D360 Concepts | Status |
|-------|------|---------------|--------|
| [01-synthetic-data](01-synthetic-data/) | Generate & load CRM data via Python + REST API | CRM-native ingestion, data model foundation | Complete |
| [02-external-data](02-external-data/) | Create Delta tables in Databricks via SQL API | External data sources, Zero Copy, Query Federation | Complete |
| [03-d360-config](03-d360-config/) | Connect Databricks, create data streams, map DMOs, configure IR | Data Streams, DLOs, DMOs, Identity Resolution, Calculated Insights, Segments | Complete |
| [04-agentforce-agent](04-agentforce-agent/) | Design agent grounded in unified D360 data | Prompt templates, Agentforce + D360 integration, Trust Layer | Complete |

## Key D360 Concepts Demonstrated

### Data Ingestion
- **CRM Native Ingestion** -- Salesforce objects ingested with zero connector cost
- **Query Federation (Zero Copy)** -- Databricks Delta tables queried live, no data movement
- **Direct Access (Accelerated)** -- Zero Copy with local caching for performance

### Data Modeling
- **Data Lake Objects (DLOs)** -- Raw data containers preserving source schema
- **Data Model Objects (DMOs)** -- Normalized canonical model for cross-source analysis
- **Individual-Level Data** -- Web analytics and product usage keyed by `user_email`, not company domain

### Data Unification
- **Identity Resolution** -- Matching individuals across sources via Contact Point Email (exact email match)
- **Contact Point Email** -- The bridge object that links Individual DMO records to email addresses for IR matching
- **Unified Individuals** -- Single person view: CRM contact + web behavior + product usage, all matched by email

### Data Activation
- **Calculated Insights** -- Health Score computed from web engagement, product usage, and support case data
- **Segments** -- At Risk, Upsell Ready, Healthy groupings based on Health Score thresholds
- **Agentforce** -- AI agents grounded in the unified, trusted data with prompt templates

## Technical Stack

- **Python** -- Data generation (Faker, pandas) and Salesforce REST API (simple_salesforce)
- **Databricks** -- Delta tables, SQL Warehouse, REST API for programmatic setup
- **Salesforce** -- Data Cloud (D360), Agentforce Studio, SF CLI for OAuth
- **Auth** -- SF CLI OAuth (browser flow), Databricks PAT, no SOAP API needed
