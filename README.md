# Bruno's Data + AI Labs

Hands-on labs exploring **Data + AI + CRM** architecture patterns with Salesforce Data Cloud (D360), Databricks, and Agentforce.

## Architecture

```
 Salesforce CRM              Databricks (Delta Lake)
 ┌────────────┐              ┌──────────────────┐
 │ Accounts   │              │ Web Analytics    │
 │ Contacts   │  CRM Native  │ Product Usage    │  Query Federation
 │ Opps/Cases │  Ingestion   │ Firmographic     │  (Zero Copy)
 └─────┬──────┘              └────────┬─────────┘
       │                              │
       ▼                              ▼
 ┌────────────────────────────────────────────┐
 │         Salesforce Data Cloud (D360)        │
 │                                            │
 │  DLOs → DMOs → Identity Resolution        │
 │          ↓                                 │
 │  Calculated Insights → Segments           │
 │          ↓                                 │
 │      Agentforce Agent                      │
 │  (grounded in unified data)                │
 └────────────────────────────────────────────┘
```

## Labs

### [D360 + Agentforce Lab](d360-agentforce-lab/)

End-to-end D360 pipeline: synthetic B2B data → Databricks Delta tables → Data Cloud Query Federation → Agentforce agent design.

**What's inside:**
- Python scripts to populate Salesforce CRM with realistic B2B data (25 accounts, 62 contacts, 40 opportunities, 18 cases)
- Databricks Delta tables created programmatically via REST API (web analytics, product usage, firmographic enrichment)
- Data Cloud configuration: 7 data streams, DLO-to-DMO mapping, identity resolution architecture
- Agentforce agent design: prompt templates, actions, and grounding in unified D360 data

**D360 concepts covered:** CRM Native Ingestion, Query Federation (Zero Copy), Data Streams, DLOs, DMOs, Identity Resolution, Calculated Insights, Segmentation, Agentforce grounding

## Certifications

- Databricks Certified Generative AI Engineer
- Microsoft Certified Azure AI Engineer Associate
- AWS Certified Machine Learning Engineer Associate
- Google Cloud Professional Machine Learning Engineer

## Tech Stack

| Technology | Usage |
|-----------|-------|
| Python | Data generation, REST API scripting |
| Salesforce Data Cloud | Data unification, identity resolution |
| Databricks | Delta Lake, SQL Warehouse, Unity Catalog |
| Agentforce | AI agent grounded in unified data |
| SF CLI | OAuth authentication |

---

All data in this repository is synthetic. No real credentials, API keys, or proprietary data from any employer.
