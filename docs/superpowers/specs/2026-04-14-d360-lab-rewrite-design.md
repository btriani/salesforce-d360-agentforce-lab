# D360 + Agentforce Lab — Full Rewrite Design Spec

## Problem Statement

The lab's Identity Resolution (IR) was broken because all external data (web analytics, product usage, firmographic) was keyed at the **company/domain level**, but D360 IR matches **individuals** (people) via Contact Point objects. With no individual-level identifiers in external data, IR silently produced zero matches — forcing dozens of manual data links in the Data Cloud UI.

Additionally, Phases 3 (D360 Configuration) and 4 (Agentforce Agent) were incomplete: Calculated Insights, Segments, and the agent itself were referenced but never defined.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Approach | Full rewrite (all 4 phases) | Clean architecture, coherent teaching narrative |
| IR data model | Hybrid: individual-level for web/product, account-level for firmographic | Teaches both IR (person matching) and DMO relationships (company linking) |
| Teaching content | Inline callouts + Field Notes per phase | Callouts prevent students from hitting walls; Field Notes provide architectural depth |
| Documentation | Written guides only, no screenshots | More maintainable; forces students to learn the UI |
| Diagrams | Mermaid diagrams in all READMEs | Render natively on GitHub; visual architecture is critical for teaching |
| Scope | D360 lab only | Portfolio structure is a separate concern |

## Architecture Overview

```
Sources                          D360                              Output
┌─────────────────┐    ┌─────────────────────────────────┐    ┌──────────────┐
│ Phase 1: CRM    │───>│ DLOs ──> DMOs ──> IR            │    │ Phase 4:     │
│ 25 Accounts     │    │  (raw)   (normalized) (matching)│    │ Agentforce   │
│ ~55 Contacts    │    │                                 │    │ Agent        │
│ ~35 Opps        │    │ Contact Point Email             │    │              │
│ ~18 Cases       │    │ (formula PK, Party ID)          │───>│ Actions:     │
├─────────────────┤    │                                 │    │ - Briefing   │
│ Phase 2: Ext    │───>│ Calculated Insight:             │    │ - At Risk    │
│ Web Analytics   │    │ Customer Health Score           │    │ - Next Best  │
│ Product Usage   │    │                                 │    │ - Upsell     │
│ Firmographic    │    │ Segments:                       │    │              │
└─────────────────┘    │ At Risk / Healthy / Upsell Ready│    └──────────────┘
                       └─────────────────────────────────┘
                                  Phase 3
```

---

## Phase 1: CRM Data Generation (Rewrite)

### What stays the same

- 25 accounts across 5 industries (Financial Services, Healthcare, Retail, Manufacturing, Technology)
- Hardcoded company list with domains (apexfintech.com, meridianpay.io, etc.)
- ~55 contacts (2-3 per account) with role-weighted titles
- ~35 opportunities (1-2 per account) with industry-specific deal types
- ~18 cases with industry-specific support subjects
- Email format: `{firstname}.{lastname}@{domain}`
- Faker.seed(42) and random.seed(42) for reproducibility
- SF CLI OAuth authentication (no SOAP)
- `simple_salesforce` for REST API loading

### What changes

1. **New export: `contact_reference.json`**
   - Phase 2 needs contact-level data to generate individual-level external data
   - Structure per record:
     ```json
     {
       "email": "jane.doe@apexfintech.com",
       "first_name": "Jane",
       "last_name": "Doe",
       "title": "CTO",
       "department": "Engineering",
       "account_name": "Apex Financial Technologies",
       "domain": "apexfintech.com",
       "salesforce_contact_id": "003...",
       "salesforce_account_id": "001..."
     }
     ```

2. **Email uniqueness validation**
   - Before loading contacts, check for duplicate emails within the same account
   - If collision detected, append a number suffix: `jane.doe2@apexfintech.com`

3. **Deterministic phone numbers**
   - Replace `Faker.phone_number()` with seeded format: `(555) {3-digit}-{4-digit}` using `random.randint()`
   - Ensures reproducibility across runs

4. **Teaching content additions**
   - README with inline callouts explaining CRM-native ingestion
   - Field Notes section covering: why OAuth over SOAP, why `simple_salesforce`, what happens when you load into a Data Cloud-enabled org

### Files

- `generate_and_load.py` — rewritten
- `requirements.txt` — unchanged
- `README.md` — rewritten with Mermaid diagrams and teaching content
- `company_reference.json` — generated output (unchanged format)
- `contact_reference.json` — new generated output

---

## Phase 2: External Data Generation (Rewrite — Major Changes)

### Data Model Restructuring

The core fix: web analytics and product usage become **individual-level** (keyed by `user_email`), while firmographic stays **account-level** (keyed by `domain`).

### Table 1: Web Analytics (Individual-Level)

- **Rows:** ~44 (~80% of contacts; ~20% excluded because not everyone visits the website)
- **Key:** `user_email` (matches CRM Contact email — this is what IR matches on)
- **Exclusion logic:** Deterministic by role. Excluded roles: VP of Sales (0% chance), Head of Customer Success (0% chance). All other roles included (100% chance). Then 5 random contacts from included roles are also excluded to simulate incomplete tracking.

| Field | Type | Purpose |
|-------|------|---------|
| `user_email` | STRING | Primary key; IR match key (exact email) |
| `company_domain` | STRING | Account-level grouping |
| `page_views_30d` | INT | Engagement signal |
| `product_pages_viewed` | INT | Interest depth |
| `demo_page_visits` | INT | Sales intent signal |
| `avg_session_minutes` | DOUBLE | Engagement quality |
| `last_visit_date` | DATE | Recency signal |

### Table 2: Product Usage (Individual-Level)

- **Rows:** ~38 (~70% of contacts; executives and sales contacts excluded — they don't log into the product)
- **Key:** `user_email` (matches CRM Contact email)
- **Exclusion logic:** Deterministic by role. Excluded roles: VP of Sales (0%), Head of Customer Success (0%), Director of Product (0%), VP of Engineering (50% chance — some VPs still use the product). All other roles included (100%). Realistic: non-technical roles don't have product logins.

| Field | Type | Purpose |
|-------|------|---------|
| `user_email` | STRING | Primary key; IR match key (exact email) |
| `company_domain` | STRING | Account-level grouping |
| `account_id_external` | STRING | External system ID (EXT-XXXXX format) |
| `feature_adoption_score` | INT | Health signal (15-95 range) |
| `api_calls_30d` | INT | Usage volume |
| `active_users` | INT | Per-company metric (same for all users at a company) |
| `last_login_date` | DATE | Recency / churn signal |
| `data_volume_gb` | DOUBLE | Utilization metric |

### Table 3: Firmographic Enrichment (Account-Level — Unchanged Concept)

- **Rows:** 25 (all accounts)
- **Key:** `domain` (links to Account DMO via domain field — no IR)

| Field | Type | Purpose |
|-------|------|---------|
| `domain` | STRING | Primary key; account match via DMO relationship |
| `company_name` | STRING | ~20% have variations (Inc., LLC, uppercase, double spaces) |
| `employee_count` | INT | Company size (+/- variance from CRM) |
| `annual_revenue_estimate` | LONG | Revenue estimate |
| `funding_stage` | STRING | Seed, Series A/B/C, Growth, Public, Private |
| `tech_stack_tags` | STRING | Comma-separated technology tags |

### Intentional Data Quality Challenges

| Challenge | Implementation | What It Teaches |
|-----------|---------------|-----------------|
| Partial coverage | Web: ~80%, Product: ~70% of contacts | D360 builds profiles from whatever sources are available |
| Foreign key mismatch | Product usage uses EXT-XXXXX, not SF IDs | IR works on attributes (email), not foreign keys |
| Name variations | ~20% of firmographic names have Inc., LLC, etc. | Fuzzy matching in reconciliation rules |
| Role-based exclusions | Execs excluded from product usage, sales from web analytics | Not all individuals appear in all systems |

### Files

- `generate_external_data.py` — rewritten (reads `contact_reference.json` from Phase 1)
- `databricks_create_delta_tables.py` — rewritten to match new schema
- `README.md` — rewritten with Mermaid data model diagram and teaching content
- `csv_exports/` — generated CSV output

---

## Phase 3: D360 Configuration (Complete Rewrite — Previously Documentation Only)

### Guide Structure: 6 Steps

#### Step 1: Connect Data Sources (Data Streams)

Configure 7 data streams:

| # | Stream | Source | Type | Category | Expected Rows |
|---|--------|--------|------|----------|---------------|
| 1 | Account_Home | CRM | Native Ingestion | Profile | 25 |
| 2 | Contact_Home | CRM | Native Ingestion | Profile | ~55 |
| 3 | Opportunity_Home | CRM | Native Ingestion | Engagement | ~35 |
| 4 | Case_Home | CRM | Native Ingestion | Engagement | ~18 |
| 5 | Web Analytics | Databricks | Query Federation (Direct Access) | Engagement | ~44 |
| 6 | Product Usage | Databricks | Query Federation (Direct Access) | Engagement | ~38 |
| 7 | Firmographic | Databricks | Query Federation (Direct Access) | Profile | 25 |

Inline callout: CRM-native ingestion is free and automatic — this is D360's key advantage over standalone CDPs.

#### Step 2: Map DLOs to DMOs

Map raw Data Lake Objects to normalized Data Model Objects:

**Standard DMOs:**

| DLO | DMO | Key Field Mappings |
|-----|-----|--------------------|
| Account_Home | Account | Name, Website, Industry, NumberOfEmployees, AnnualRevenue |
| Contact_Home | Individual | FirstName, LastName, Email → Contact Point Email |
| Opportunity_Home | Sales Order | Name, Amount, StageName, CloseDate, Probability |
| Case_Home | Case | Subject, Priority, Status, Origin |

**Custom DMOs:**

| DLO | DMO | Key Field Mappings |
|-----|-----|--------------------|
| Web Analytics | Web Analytics (custom) | user_email, company_domain, page_views_30d, demo_page_visits, last_visit_date |
| Product Usage | Product Usage (custom) | user_email, company_domain, feature_adoption_score, api_calls_30d, last_login_date |
| Firmographic | Firmographic Enrichment (custom) | domain, company_name, employee_count, funding_stage, tech_stack_tags |

Inline callout: The two-layer model (DLO → DMO) is D360's version of ELT. DLOs are the raw "Extract + Load"; DMOs are the "Transform" into a canonical model.

#### Step 3: Configure Contact Points & Identity Resolution

This is the step that was broken before. Detailed walkthrough:

1. **Enable Individual DMO** — ensure the Sales Cloud data bundle is deployed
2. **Create Contact Point Email records:**
   - Map Contact email to Contact Point Email DMO
   - Formula-based composite primary key: `{ContactId} + "_email"`
   - Party ID links Contact Point Email → Individual
3. **Map external data to Individual DMO + Contact Point Email:**
   - Web Analytics and Product Usage each map `user_email` to both:
     - **Individual DMO** — creates an Individual record per person per source
     - **Contact Point Email DMO** — creates a Contact Point Email linked to that Individual via Party ID
   - This means each source produces its own Individual + Contact Point Email records
   - IR then compares Contact Point Emails across sources and merges matching Individuals
4. **Configure Match Rule:**
   - Rule type: Exact Match
   - Match field: Contact Point Email → Email Address
   - When two Contact Point Email records share the same email address, IR unifies their parent Individuals
5. **Run Identity Resolution** and verify:
   - Expected: ~44 web analytics contacts matched to CRM contacts
   - Expected: ~38 product usage contacts matched to CRM contacts
   - Overlapping contacts (in both web + product) should resolve to a single unified Individual

Lesson Learned callout: "When external data only has company domains (no emails), IR can't match at the Individual level. D360 silently produces zero matches — no error, no warning. You end up manually linking records because the automated matching has nothing to work with. The fix: external data must include the same individual-level identifiers (email) that exist in CRM Contacts. IR matches people, not companies."

#### Step 4: Link Firmographic via DMO Relationships

Connect Firmographic Enrichment (custom DMO) to Account (standard DMO) using the `domain` field:

1. Create a relationship field on Firmographic DMO pointing to Account DMO
2. Map `firmographic.domain` to match `Account.Website` (domain extracted)
3. No IR needed — this is a direct data model relationship

Inline callout: "This is the second integration pattern. IR handles people (Individual matching via email). DMO relationships handle companies (Account linking via domain). Real D360 implementations use both."

#### Step 5: Build Calculated Insight — Customer Health Score

Formula: weighted composite score (0-100 per account)

```
Health Score = (
    Product_Adoption_Score   × 0.40    # feature_adoption_score (0-100)
  + Web_Engagement_Score     × 0.20    # normalized page_views + demo_visits
  + Support_Health_Score     × 0.20    # inverse of case severity/count
  + Deal_Momentum_Score      × 0.20    # opp stage progression + amount
)
```

**Component definitions:**

| Component | Source | Calculation | Range |
|-----------|--------|-------------|-------|
| Product Adoption | Product Usage DMO | Average `feature_adoption_score` across all users at the account | 0-100 |
| Web Engagement | Web Analytics DMO | Normalize: `min(page_views_30d / 500, 1) × 50 + min(demo_page_visits / 3, 1) × 50` | 0-100 |
| Support Health | Case DMO | `100 - (open_cases × 15 + escalated_cases × 25)`, floor at 0 | 0-100 |
| Deal Momentum | Sales Order DMO | `avg(Probability)` across open opps; 0 if no open opps | 0-100 |

Inline callout: "Calculated Insights run on unified data — that's the whole point. Without D360, you'd need to ETL product usage, web analytics, and CRM data into a warehouse, write SQL to join them, compute the score, and push it back. D360 does this natively because the data is already unified."

#### Step 6: Create Segments

Three segments based on Health Score and activity signals:

| Segment | Criteria | Expected Count |
|---------|----------|----------------|
| At Risk | Health Score < 40 | ~7-8 accounts |
| Healthy | Health Score 40-74 | ~10-12 accounts |
| Upsell Ready | Health Score ≥ 75 AND demo_page_visits > 0 AND has open pipeline | ~5-7 accounts |

### Field Notes Section

Broader reflections and architecture insights for each step:
- Why the two-layer DLO/DMO model exists (schema evolution, source independence)
- Why Contact Point objects need formula-based PKs (deterministic IDs for cross-source matching)
- The difference between Profile and Engagement data categories and when to use each
- Why CRM-native ingestion is D360's moat against standalone CDPs
- Production considerations: DevOps Data Kits, `sf project deploy start`, CI/CD

### Files

- `README.md` — complete step-by-step guide with Mermaid diagrams, inline callouts, and Field Notes

---

## Phase 4: Agentforce Agent (Written from Scratch)

### Agent Identity

- **Name:** D360 Account Intelligence Agent
- **Purpose:** Provide sales and CS reps with unified account intelligence grounded in D360 data
- **Persona:** Knowledgeable account analyst that cites specific data points

### Agent Actions

| # | Action | Trigger | Data Sources | Output |
|---|--------|---------|--------------|--------|
| 1 | Account Briefing | "Brief me on {Account}" | Unified profiles + firmographic + all contacts' activity | Full 360 view with health score, risk signals, recommendations |
| 2 | At Risk Detection | "Which accounts are at risk?" | At Risk segment + Health Score + recent cases | Ranked list with specific risk signals |
| 3 | Next Best Action | "What should I do about {Account}?" | Health Score + segment + all activity signals | Prioritized recommendations with urgency levels |
| 4 | Upsell Candidates | "Who's ready for upsell?" | Upsell Ready segment + deal stage + web signals | Ranked accounts with readiness evidence |

### Prompt Template (Account Briefing)

```
You are an Account Intelligence Agent for a B2B SaaS company.
You have access to unified customer data from Salesforce Data Cloud.

## Account Context
Account: {!Account.Name}
Industry: {!Account.Industry}
Health Score: {!CalculatedInsight.CustomerHealthScore}/100
Segment: {!Segment.Membership}
Firmographic: {!Firmographic.FundingStage}, {!Firmographic.EmployeeCount} employees

## Recent Activity (last 30 days)
Web Engagement: {!WebAnalytics.PageViews30d} page views, {!WebAnalytics.DemoPageVisits} demo visits
Product Usage: adoption score {!ProductUsage.FeatureAdoptionScore}, {!ProductUsage.ApiCalls30d} API calls
Last Login: {!ProductUsage.LastLoginDate}
Open Cases: {!Case.OpenCount} ({!Case.EscalatedCount} escalated)
Pipeline: {!Opportunity.OpenCount} open, total value {!Opportunity.TotalAmount}

## Instructions
Provide a comprehensive account briefing. Highlight:
1. Overall account health with specific evidence
2. Key risk signals or positive trends
3. Recommended next actions with urgency level
4. Which contacts to engage and why (based on their individual activity)
```

### Einstein Trust Layer

- **Data Grounding:** Agent responses must cite specific D360 data. No hallucinated metrics.
- **Access Control:** Agent respects Salesforce sharing rules and field-level security.
- **Audit Trail:** Every agent response logged with data sources accessed.

### The D360 Difference

The README includes a side-by-side comparison: same question asked with CRM-only data vs. unified D360 data. Demonstrates the value proposition:

- **Without D360:** "Apex Financial Technologies has 2 open opportunities worth $380K and 1 escalated case."
- **With D360:** "Apex Financial Technologies (Series C) has Health Score 34 — AT RISK. Product adoption dropped to 38%, CTO hasn't logged in for 23 days but visited competitor comparison page 4 times. Recommend: escalate to CS leadership, schedule QBR within 5 days."

### Files

- `README.md` — agent design guide with Mermaid diagrams, prompt templates, and the D360 comparison

---

## Root README Updates

The root `README.md` will be rewritten to reflect the redesigned architecture:

- Updated Mermaid architecture diagram showing individual-level vs account-level data flow
- Updated lab structure table with accurate descriptions
- Updated data flow diagram reflecting email-keyed external data
- Updated Identity Resolution diagram showing the two integration paths
- Preserved: platform comparison chart, vocabulary table, tech stack, observations section
- New: "Lessons from Building This Lab" section with condensed Field Notes

---

## Deliverables Summary

| Phase | Files | Status |
|-------|-------|--------|
| Phase 1 | `generate_and_load.py`, `README.md`, `requirements.txt` | Rewrite |
| Phase 2 | `generate_external_data.py`, `databricks_create_delta_tables.py`, `README.md` | Major rewrite |
| Phase 3 | `README.md` (comprehensive step-by-step guide) | Written from scratch |
| Phase 4 | `README.md` (agent design + prompt templates) | Written from scratch |
| Root | `README.md` | Rewrite |
| Root | `.gitignore` | Minor update (already done) |

## Out of Scope

- Empty placeholder directories (`certifications/`, `databricks-ml-projects/`)
- Portfolio-level repo structure
- Screenshots or video content
- GitHub Actions automation (mentioned in tech stack as "planned")
- Production deployment guides
