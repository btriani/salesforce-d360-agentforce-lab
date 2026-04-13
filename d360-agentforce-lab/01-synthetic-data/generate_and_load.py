"""
Phase 1: Generate and Load Synthetic B2B Data into Salesforce CRM
=================================================================

D360 Concept: This is the CRM data that Data Cloud (D360) ingests natively.
Salesforce-to-Salesforce ingestion is "free" — no connectors needed.
Data Cloud treats CRM objects as first-class data sources.

What we create:
  - 25 Accounts (B2B companies across fintech, healthcare, retail, manufacturing, tech)
  - 55 Contacts linked to Accounts (CTOs, VPs, Heads of Data, etc.)
  - 35 Opportunities at various stages with realistic deal sizes ($50K–$500K)
  - 18 Cases (support tickets with varying priority and status)

Why this matters for the interview:
  - Shows you understand the CRM-native data model that D360 unifies
  - The Account domains we set here will be used in Phase 2 for identity resolution
  - The variety of stages/statuses creates realistic segments and calculated insights later
"""

import os
import sys
import json
import random
import subprocess
from datetime import datetime, timedelta
from simple_salesforce import Salesforce
from faker import Faker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

fake = Faker()
Faker.seed(42)  # Reproducible data — same run = same data
random.seed(42)

# SF CLI alias — change this if you used a different alias with sf org login web
SF_ORG_ALIAS = "my-dev-org"

# ---------------------------------------------------------------------------
# Salesforce Connection
# ---------------------------------------------------------------------------

def connect_to_salesforce():
    """
    Connect to Salesforce using an access token from the SF CLI.

    We authenticate via 'sf org login web' (OAuth browser flow), then
    grab the access token from the CLI. This avoids SOAP API entirely —
    simple_salesforce accepts a session_id + instance_url directly.

    D360 Interview Note: In production, D360 ingests CRM data automatically.
    We're using the REST API here only to POPULATE the org with test data.
    """
    print(f"🔗 Getting access token from SF CLI (alias: {SF_ORG_ALIAS})...")

    try:
        result = subprocess.run(
            ["sf", "org", "display", "--target-org", SF_ORG_ALIAS, "--json"],
            capture_output=True, text=True, check=True,
        )
        org_info = json.loads(result.stdout)["result"]
    except FileNotFoundError:
        print("\n❌ Salesforce CLI (sf) not found.")
        print("   Install it: brew install sf")
        print("   Then authenticate: sf org login web --alias my-dev-org")
        sys.exit(1)
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        print(f"\n❌ Failed to get org info from SF CLI: {e}")
        print("   Make sure you've authenticated: sf org login web --alias my-dev-org")
        sys.exit(1)

    access_token = org_info["accessToken"]
    instance_url = org_info["instanceUrl"]
    username = org_info["username"]

    print(f"   User: {username}")
    print(f"   Instance: {instance_url}")

    # Pass token directly to simple_salesforce — no SOAP login needed
    sf = Salesforce(instance_url=instance_url, session_id=access_token)
    print(f"✅ Connected via REST API!")
    return sf


# ---------------------------------------------------------------------------
# Data Definitions
# ---------------------------------------------------------------------------

# Realistic B2B companies — we control the domains so Phase 2 external data
# can reference them for identity resolution testing.
COMPANIES = [
    # Fintech
    {"name": "Apex Financial Technologies", "domain": "apexfintech.com", "industry": "Financial Services", "employees": 450, "revenue": 85_000_000},
    {"name": "Meridian Payments Group", "domain": "meridianpay.io", "industry": "Financial Services", "employees": 220, "revenue": 42_000_000},
    {"name": "Vaultline Digital Banking", "domain": "vaultline.com", "industry": "Financial Services", "employees": 380, "revenue": 67_000_000},
    {"name": "ClearEdge Capital Systems", "domain": "clearedgecap.com", "industry": "Financial Services", "employees": 150, "revenue": 28_000_000},
    {"name": "Fintrust Solutions", "domain": "fintrust.io", "industry": "Financial Services", "employees": 95, "revenue": 15_000_000},

    # Healthcare
    {"name": "Novus Health Analytics", "domain": "novushealth.com", "industry": "Healthcare", "employees": 600, "revenue": 120_000_000},
    {"name": "BioSync Medical Systems", "domain": "biosyncmed.com", "industry": "Healthcare", "employees": 340, "revenue": 55_000_000},
    {"name": "CarePoint Digital", "domain": "carepointdigital.com", "industry": "Healthcare", "employees": 180, "revenue": 32_000_000},
    {"name": "MedLattice Inc", "domain": "medlattice.com", "industry": "Healthcare", "employees": 520, "revenue": 98_000_000},
    {"name": "Helix Genomics Platform", "domain": "helixgenomics.io", "industry": "Healthcare", "employees": 275, "revenue": 48_000_000},

    # Retail / E-commerce
    {"name": "UrbanThread Retail", "domain": "urbanthread.com", "industry": "Retail", "employees": 1200, "revenue": 230_000_000},
    {"name": "Shopwise Commerce", "domain": "shopwise.io", "industry": "Retail", "employees": 310, "revenue": 58_000_000},
    {"name": "FreshCart Marketplace", "domain": "freshcart.com", "industry": "Retail", "employees": 480, "revenue": 92_000_000},
    {"name": "Lumenaire Brands", "domain": "lumenaire.com", "industry": "Retail", "employees": 200, "revenue": 38_000_000},
    {"name": "TrueNorth Outdoor Co", "domain": "truenorthoutdoor.com", "industry": "Retail", "employees": 160, "revenue": 25_000_000},

    # Manufacturing
    {"name": "Forgewell Industries", "domain": "forgewell.com", "industry": "Manufacturing", "employees": 2100, "revenue": 450_000_000},
    {"name": "Steelvine Manufacturing", "domain": "steelvine.com", "industry": "Manufacturing", "employees": 850, "revenue": 180_000_000},
    {"name": "Precision Dynamics Corp", "domain": "precisiondynamics.com", "industry": "Manufacturing", "employees": 620, "revenue": 130_000_000},
    {"name": "Cascade Materials Group", "domain": "cascadematerials.com", "industry": "Manufacturing", "employees": 430, "revenue": 78_000_000},
    {"name": "Ironclad Components", "domain": "ironcladcomp.com", "industry": "Manufacturing", "employees": 290, "revenue": 52_000_000},

    # Technology / SaaS
    {"name": "Neuralink Data Systems", "domain": "neuralinkdata.com", "industry": "Technology", "employees": 750, "revenue": 160_000_000},
    {"name": "CloudPeak Software", "domain": "cloudpeak.io", "industry": "Technology", "employees": 400, "revenue": 75_000_000},
    {"name": "DataVista Analytics", "domain": "datavista.com", "industry": "Technology", "employees": 190, "revenue": 35_000_000},
    {"name": "Quantum Edge Labs", "domain": "quantumedgelabs.com", "industry": "Technology", "employees": 130, "revenue": 22_000_000},
    {"name": "Synthetica AI", "domain": "synthetica.ai", "industry": "Technology", "employees": 85, "revenue": 12_000_000},
]

# Roles for Contacts — weighted toward technical/data titles
# (these are the personas who would use D360 and interact with Agentforce)
CONTACT_ROLES = [
    ("CTO", 0.08),
    ("VP of Engineering", 0.10),
    ("Head of Data", 0.12),
    ("Director of Analytics", 0.10),
    ("Data Engineer", 0.12),
    ("VP of Sales", 0.08),
    ("Head of Customer Success", 0.10),
    ("Director of Product", 0.08),
    ("Chief Data Officer", 0.06),
    ("Solutions Architect", 0.08),
    ("IT Director", 0.08),
]

# Opportunity stages with realistic progression probabilities
OPP_STAGES = [
    "Prospecting",
    "Qualification",
    "Needs Analysis",
    "Value Proposition",
    "Proposal/Price Quote",
    "Negotiation/Review",
    "Closed Won",
    "Closed Lost",
]

# Case priorities and statuses
CASE_PRIORITIES = ["Low", "Medium", "High", "Critical"]  # Critical may not exist in all orgs
CASE_STATUSES = ["New", "Working", "Escalated", "Closed"]


# ---------------------------------------------------------------------------
# Data Generation Functions
# ---------------------------------------------------------------------------

def generate_accounts():
    """
    Generate Account records from our company definitions.

    D360 Note: Account is a standard CRM object. In Data Cloud, it maps to
    the Account Data Model Object (DMO). D360 ingests this automatically
    from the CRM — no connector config needed.
    """
    accounts = []
    for company in COMPANIES:
        accounts.append({
            "Name": company["name"],
            "Website": f"https://www.{company['domain']}",
            "Industry": company["industry"],
            "NumberOfEmployees": company["employees"],
            "AnnualRevenue": company["revenue"],
            "Description": f"B2B {company['industry'].lower()} company. Domain: {company['domain']}",
            "Phone": fake.phone_number(),
        })
    return accounts


def generate_contacts(account_ids_and_names):
    """
    Generate Contact records linked to Accounts.

    D360 Note: Contact maps to the Individual DMO in Data Cloud.
    Individual is the core entity for identity resolution — D360 matches
    Contacts with external data (web analytics, etc.) to build unified profiles.

    We generate 2-3 contacts per account, with email addresses using the
    company domain. This is intentional: Phase 2's web analytics data uses
    the same domains, enabling identity resolution by email-to-domain matching.
    """
    contacts = []
    roles = [r[0] for r in CONTACT_ROLES]
    weights = [r[1] for r in CONTACT_ROLES]

    for account_id, company in account_ids_and_names:
        # 2-3 contacts per account
        num_contacts = random.choice([2, 2, 3, 3, 3])
        domain = company["domain"]
        used_roles = random.sample(
            roles, k=min(num_contacts, len(roles)),
        )

        for i in range(num_contacts):
            first_name = fake.first_name()
            last_name = fake.last_name()
            role = used_roles[i] if i < len(used_roles) else random.choices(roles, weights=weights, k=1)[0]

            contacts.append({
                "AccountId": account_id,
                "FirstName": first_name,
                "LastName": last_name,
                "Title": role,
                "Email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "Phone": fake.phone_number(),
                "Department": _role_to_department(role),
            })

    return contacts


def _role_to_department(role):
    """Map a job title to a department."""
    mapping = {
        "CTO": "Engineering",
        "VP of Engineering": "Engineering",
        "Head of Data": "Data",
        "Director of Analytics": "Data",
        "Data Engineer": "Data",
        "VP of Sales": "Sales",
        "Head of Customer Success": "Customer Success",
        "Director of Product": "Product",
        "Chief Data Officer": "Data",
        "Solutions Architect": "Engineering",
        "IT Director": "IT",
    }
    return mapping.get(role, "General")


def generate_opportunities(account_ids_and_names):
    """
    Generate Opportunity records at various stages.

    D360 Note: Opportunities feed into Calculated Insights. In Phase 3,
    we'll create a Customer Health Score that factors in Opportunity stage,
    deal size, and velocity. Having a mix of stages (including Closed Won/Lost)
    makes the Calculated Insight meaningful.

    Deal sizes range from $50K to $500K, with dates spread over last 12 months.
    """
    opportunities = []
    today = datetime.now()

    for account_id, company in account_ids_and_names:
        # 1-2 opportunities per account (some accounts get more to reach ~35 total)
        num_opps = random.choices([1, 1, 2, 2, 2], k=1)[0]

        for _ in range(num_opps):
            stage = random.choice(OPP_STAGES)
            amount = random.randint(50, 500) * 1000  # $50K to $500K in $1K increments
            days_ago = random.randint(10, 365)
            close_date = today + timedelta(days=random.randint(-30, 90))

            # Closed deals should have close dates in the past
            if stage in ("Closed Won", "Closed Lost"):
                close_date = today - timedelta(days=random.randint(5, 180))

            opp_name = f"{company['name']} - {_deal_type(company['industry'])} ({stage.split('/')[0]})"

            opportunities.append({
                "AccountId": account_id,
                "Name": opp_name[:120],  # Salesforce name field limit
                "StageName": stage,
                "Amount": amount,
                "CloseDate": close_date.strftime("%Y-%m-%d"),
                "Probability": _stage_probability(stage),
                "Description": f"Enterprise deal with {company['name']}. Industry: {company['industry']}.",
            })

    return opportunities


def _deal_type(industry):
    """Generate a realistic deal type based on industry."""
    types = {
        "Financial Services": ["Platform License", "Risk Analytics Suite", "Compliance Module"],
        "Healthcare": ["Clinical Data Platform", "Patient Analytics", "EHR Integration"],
        "Retail": ["Commerce Platform", "Customer Analytics", "Inventory Intelligence"],
        "Manufacturing": ["IoT Platform", "Supply Chain Analytics", "Quality Management"],
        "Technology": ["Enterprise License", "Data Platform", "API Suite"],
    }
    return random.choice(types.get(industry, ["Enterprise License"]))


def _stage_probability(stage):
    """Map Opportunity stage to win probability."""
    probs = {
        "Prospecting": 10,
        "Qualification": 20,
        "Needs Analysis": 30,
        "Value Proposition": 50,
        "Proposal/Price Quote": 65,
        "Negotiation/Review": 80,
        "Closed Won": 100,
        "Closed Lost": 0,
    }
    return probs.get(stage, 50)


def generate_cases(account_ids_and_names, contact_ids_by_account):
    """
    Generate Case records (support tickets).

    D360 Note: Cases are critical for the Customer Health Score calculated insight.
    High-priority open cases are a strong signal of "At Risk" accounts.
    In Phase 3, we'll segment accounts with open high-priority cases + declining
    engagement as "At Risk" — exactly the kind of actionable insight that
    Agentforce agents surface to customer success teams.
    """
    cases = []
    today = datetime.now()

    # Pick ~18 accounts to have cases (not all accounts have support issues)
    accounts_with_cases = random.sample(account_ids_and_names, min(18, len(account_ids_and_names)))

    for account_id, company in accounts_with_cases:
        priority = random.choice(["Low", "Medium", "Medium", "High", "High"])
        status = random.choice(["New", "Working", "Escalated", "Closed", "Closed"])
        days_ago = random.randint(1, 90)

        # Get a contact for this account if available
        contact_id = None
        if account_id in contact_ids_by_account and contact_ids_by_account[account_id]:
            contact_id = random.choice(contact_ids_by_account[account_id])

        subject = _case_subject(company["industry"])

        case_data = {
            "AccountId": account_id,
            "Subject": subject,
            "Description": f"Support request from {company['name']}: {subject}",
            "Priority": priority,
            "Status": status,
            "Origin": random.choice(["Web", "Phone", "Email"]),
        }
        if contact_id:
            case_data["ContactId"] = contact_id

        cases.append(case_data)

    return cases


def _case_subject(industry):
    """Generate a realistic support ticket subject."""
    subjects = {
        "Financial Services": [
            "API rate limiting affecting transaction processing",
            "Data export failing for compliance audit",
            "SSO integration timeout issues",
            "Dashboard not reflecting real-time balances",
        ],
        "Healthcare": [
            "HIPAA audit trail missing entries",
            "Patient data sync delay with EHR",
            "Role-based access not applying correctly",
            "Report generation timeout on large datasets",
        ],
        "Retail": [
            "Inventory sync discrepancy across channels",
            "Checkout flow error on mobile",
            "Customer segmentation not updating",
            "Product recommendation engine latency",
        ],
        "Manufacturing": [
            "IoT sensor data ingestion dropping records",
            "Supply chain dashboard showing stale data",
            "Batch processing job failing overnight",
            "Alert thresholds not triggering notifications",
        ],
        "Technology": [
            "API documentation mismatch with actual behavior",
            "Webhook delivery failures to endpoint",
            "Data pipeline backpressure causing delays",
            "Tenant isolation concern in shared environment",
        ],
    }
    return random.choice(subjects.get(industry, ["General support request"]))


# ---------------------------------------------------------------------------
# Salesforce Loading Functions
# ---------------------------------------------------------------------------

def load_accounts(sf, accounts):
    """Load Account records into Salesforce. Returns list of (sf_id, company_dict) tuples."""
    print(f"\n📊 Loading {len(accounts)} Accounts...")
    results = []
    for i, account in enumerate(accounts):
        try:
            result = sf.Account.create(account)
            sf_id = result["id"]
            results.append((sf_id, COMPANIES[i]))
            print(f"   ✓ {account['Name']} ({sf_id})")
        except Exception as e:
            print(f"   ✗ {account['Name']}: {e}")
    print(f"   → {len(results)}/{len(accounts)} Accounts created")
    return results


def load_contacts(sf, contacts):
    """Load Contact records into Salesforce. Returns dict of {account_id: [contact_ids]}."""
    print(f"\n👤 Loading {len(contacts)} Contacts...")
    contact_ids_by_account = {}
    loaded = 0
    for contact in contacts:
        try:
            result = sf.Contact.create(contact)
            contact_id = result["id"]
            acct_id = contact["AccountId"]
            contact_ids_by_account.setdefault(acct_id, []).append(contact_id)
            loaded += 1
            print(f"   ✓ {contact['FirstName']} {contact['LastName']} — {contact['Title']} ({contact_id})")
        except Exception as e:
            print(f"   ✗ {contact['FirstName']} {contact['LastName']}: {e}")
    print(f"   → {loaded}/{len(contacts)} Contacts created")
    return contact_ids_by_account


def load_opportunities(sf, opportunities):
    """Load Opportunity records into Salesforce."""
    print(f"\n💰 Loading {len(opportunities)} Opportunities...")
    loaded = 0
    for opp in opportunities:
        try:
            result = sf.Opportunity.create(opp)
            loaded += 1
            print(f"   ✓ {opp['Name'][:60]}... ${opp['Amount']:,} ({opp['StageName']})")
        except Exception as e:
            print(f"   ✗ {opp['Name'][:40]}...: {e}")
    print(f"   → {loaded}/{len(opportunities)} Opportunities created")


def load_cases(sf, cases):
    """Load Case records into Salesforce."""
    print(f"\n🎫 Loading {len(cases)} Cases...")
    loaded = 0
    for case in cases:
        try:
            result = sf.Case.create(case)
            loaded += 1
            print(f"   ✓ [{case['Priority']}] {case['Subject'][:50]}...")
        except Exception as e:
            print(f"   ✗ {case['Subject'][:40]}...: {e}")
    print(f"   → {loaded}/{len(cases)} Cases created")


# ---------------------------------------------------------------------------
# Export function — save generated data for reference and Phase 2 alignment
# ---------------------------------------------------------------------------

def export_company_reference(accounts_with_ids):
    """
    Save a JSON reference file mapping Salesforce Account IDs to company data.
    Phase 2 (Databricks) reads this to create matching external data.
    """
    reference = []
    for sf_id, company in accounts_with_ids:
        reference.append({
            "salesforce_account_id": sf_id,
            "name": company["name"],
            "domain": company["domain"],
            "industry": company["industry"],
            "employees": company["employees"],
        })

    output_path = os.path.join(os.path.dirname(__file__), "company_reference.json")
    with open(output_path, "w") as f:
        json.dump(reference, f, indent=2)
    print(f"\n📁 Company reference saved to {output_path}")
    print("   → Phase 2 will use this to create matching external data")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Phase 1: Synthetic B2B Data → Salesforce CRM")
    print("=" * 70)
    print()
    print("D360 Context: We're populating the CRM with realistic B2B data.")
    print("Data Cloud ingests CRM objects natively — this is the 'free' data")
    print("that every D360 deployment starts with. External data (Phase 2)")
    print("is where the real value of D360 shows up.")
    print()

    # Connect
    sf = connect_to_salesforce()

    # Generate and load in dependency order:
    # Accounts → Contacts → Opportunities → Cases
    # (Contacts, Opportunities, and Cases all reference Account)

    # 1. Accounts
    account_data = generate_accounts()
    account_ids = load_accounts(sf, account_data)

    # 2. Contacts (need Account IDs)
    contact_data = generate_contacts(account_ids)
    contact_ids_by_account = load_contacts(sf, contact_data)

    # 3. Opportunities (need Account IDs)
    opp_data = generate_opportunities(account_ids)
    load_opportunities(sf, opp_data)

    # 4. Cases (need Account IDs and optionally Contact IDs)
    case_data = generate_cases(account_ids, contact_ids_by_account)
    load_cases(sf, case_data)

    # 5. Export reference for Phase 2
    export_company_reference(account_ids)

    # Summary
    print()
    print("=" * 70)
    print("✅ Phase 1 Complete!")
    print("=" * 70)
    print()
    print("What was created:")
    print(f"  • {len(account_ids)} Accounts (5 industries: fintech, healthcare, retail, manufacturing, tech)")
    print(f"  • {len(contact_data)} Contacts (linked to accounts with matching email domains)")
    print(f"  • {len(opp_data)} Opportunities ($50K–$500K, various stages)")
    print(f"  • {len(case_data)} Cases (support tickets, various priorities)")
    print()
    print("D360 Interview Talking Points:")
    print("  → 'CRM data is the foundation of D360 — it ingests natively with zero config'")
    print("  → 'I set up realistic B2B data with email domains that align to external sources'")
    print("  → '  This is intentional: identity resolution needs overlapping identifiers'")
    print("  → 'The mix of opportunity stages and case priorities creates meaningful segments'")
    print()
    print("Next: Phase 2 — Create external data in Databricks (web analytics, product usage)")
    print("       The company_reference.json file bridges CRM ↔ external data")


if __name__ == "__main__":
    main()
