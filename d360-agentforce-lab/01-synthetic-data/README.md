# Phase 1: Synthetic B2B Data → Salesforce CRM

## What This Does

Generates and loads realistic B2B data into a Salesforce Developer Edition org using the REST API (`simple_salesforce`). This data becomes the CRM foundation that Data Cloud (D360) ingests natively.

## Data Created

| Object | Count | Key Fields |
|--------|-------|------------|
| Account | 25 | Name, Industry, Domain, Revenue, Employees |
| Contact | ~55 | Name, Email (uses company domain), Title, Department |
| Opportunity | ~35 | Stage, Amount ($50K–$500K), Close Date (last 12 months) |
| Case | ~18 | Subject, Priority, Status, Origin |

**Industries covered:** Financial Services, Healthcare, Retail, Manufacturing, Technology

## D360 Concepts

- **CRM-native ingestion:** Data Cloud ingests standard Salesforce objects (Account, Contact, Opportunity, Case) with zero configuration. This is the "free" data every D360 deployment starts with.
- **Data Model Objects (DMOs):** In Phase 3, these CRM objects map to standard DMOs — Account maps to Account DMO, Contact maps to Individual DMO.
- **Identity resolution setup:** Contact emails use company domains (e.g., `jane.doe@apexfintech.com`). Phase 2's web analytics data uses the same domains, creating the overlap needed for identity resolution.

## Setup

```bash
# 1. Create and activate virtual environment (from repo root)
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r d360-agentforce-lab/01-synthetic-data/requirements.txt

# 3. Configure credentials
cp d360-agentforce-lab/01-synthetic-data/.env.example d360-agentforce-lab/01-synthetic-data/.env
# Edit .env with your Salesforce credentials (see file for instructions)

# 4. Run
cd d360-agentforce-lab/01-synthetic-data
python generate_and_load.py
```

## Output

- CRM records in your Salesforce org
- `company_reference.json` — maps Salesforce Account IDs to company domains/names. Phase 2 reads this to create aligned external data.

## Files

- `generate_and_load.py` — main script (generate + load)
- `.env.example` — credential template
- `requirements.txt` — Python dependencies
- `company_reference.json` — generated after running (not committed)
