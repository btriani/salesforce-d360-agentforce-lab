# Phase 3: D360 (Data Cloud) Configuration

## What Was Configured

Step-by-step configuration of Salesforce Data Cloud to ingest, model, and unify data from CRM and Databricks sources.

### 3.1 Databricks Connector (Zero Copy / Query Federation)

Connected Databricks directly to Data Cloud — no CSV uploads, no data copying.

| Setting | Value |
|---------|-------|
| Connector Type | Databricks (Query Federation) |
| Connection Name | Databricks D360 Lab |
| Auth Method | Username & Password (PAT as password) |
| Server Hostname | `dbc-3cd549f9-402b.cloud.databricks.com:443` |
| HTTP Path | `/sql/1.0/warehouses/dbc63533d8190bea` |
| Stream Type | Direct Access (Accelerated) |

**D360 Concept — Query Federation:** Data Cloud queries the Delta tables live in Databricks and caches results locally. No data movement. This is D360's fastest-growing capability (341% YoY growth). The "Direct Access (Accelerated)" stream type means D360 caches query results for performance while keeping the source of truth in Databricks.

### 3.2 Data Streams Created

| # | Data Stream | Source | Stream Type | Records | Category |
|---|------------|--------|-------------|---------|----------|
| 1 | Account_Home | Salesforce CRM | Ingest | 38 | Profile |
| 2 | Contact_Home | Salesforce CRM | Ingest | 82 | Profile |
| 3 | Opportunity_Home | Salesforce CRM | Ingest | 71 | Engagement |
| 4 | Case_Home | Salesforce CRM | Ingest | 44 | Engagement |
| 5 | Product Usage | Databricks | Direct Access (Accelerated) | 25 | Engagement |
| 6 | Web Analytics | Databricks | Direct Access (Accelerated) | 20 | Engagement |
| 7 | Firmographic Enrichment | Databricks | Direct Access (Accelerated) | 25 | Profile |

**D360 Concept — CRM Native Ingestion:** CRM objects (Account, Contact, Opportunity, Case) are ingested natively with zero connector cost. This is a key differentiator — competitors like Segment or Tealium need to build CRM connectors. D360 treats CRM as a first-class data source.

**D360 Concept — Profile vs Engagement:** Profile data describes *what* an entity is (company attributes, firmographic data). Engagement data describes *what an entity does* (web visits, product usage, support tickets). This categorization drives how D360 handles time-series data and segmentation.

### 3.3 Data Model Mapping (DLO → DMO)

Data Lake Objects (raw ingested data) were mapped to Data Model Objects (normalized schema):

| Data Lake Object | Data Model Object | Type | Fields Mapped |
|-----------------|-------------------|------|---------------|
| Account_Home | Account | Standard DMO | 11/73 |
| Contact_Home | Individual | Standard DMO | 7+ fields |
| Opportunity_Home | Sales Order | Standard DMO | 9/53 |
| Case_Home | Case | Standard DMO | 15/56 |
| Web Analytics | Web Analytics | Custom DMO | 6/6 |
| Product Usage | Product Usage | Custom DMO | 8/8 |
| Firmographic Enrichment | Firmographic Enrichment | Custom DMO | 6/6 |

**D360 Concept — Two-Layer Data Model:** DLOs are raw data (land as-is from source). DMOs are the normalized canonical model. This separation means you can ingest from any source without worrying about schema alignment upfront, then map to the standard data model at your own pace. It's the "T" in ELT.

### 3.4 Identity Resolution

**Status:** Configuration in progress. Requires Contact Point Email/Phone DMOs with formula-based composite primary keys.

**Architecture Understanding:**
- Individual DMO is the core entity for identity resolution
- Contact Point objects (Email, Phone, Address) connect to Individual via Party ID
- Match rules use email domains, phone numbers, and names to fuzzy-match across sources
- In our scenario: Contact email domains (e.g., `jane@apexfintech.com`) would match with web analytics `company_domain` (`apexfintech.com`)

**Production Setup Notes:**
- Sales Cloud data bundle auto-provisions Contact Point mappings
- Formula fields create composite primary keys: `ContactId + "_email"` for Contact Point Email Id
- Match rule types: Exact (email), Fuzzy (name + address), Normalized (phone E.164)
- Reconciliation rules determine which source wins when data conflicts

## D360 Architecture Concepts Covered

| Concept | What It Means | Where We Saw It |
|---------|--------------|-----------------|
| CRM Native Ingestion | Zero-cost ingestion from Salesforce objects | Account, Contact, Opportunity, Case streams |
| Query Federation | Live queries against external data (no copy) | Databricks connector |
| Zero Copy | Data stays in source, D360 queries it directly | Databricks Delta tables |
| Data Streams | Pipelines that bring data into Data Cloud | 7 streams configured |
| DLO (Data Lake Object) | Raw data container, source schema preserved | 7 DLOs created |
| DMO (Data Model Object) | Normalized canonical data model | 4 standard + 3 custom DMOs |
| Profile vs Engagement | Static attributes vs time-series behavior | Category assignment on streams |
| Identity Resolution | Matching records across sources into unified profiles | Individual + Contact Points |
| Calculated Insights | Computed metrics from unified data | Next step after IR |
| Segmentation | Grouping entities by criteria | Built on top of Calculated Insights |
