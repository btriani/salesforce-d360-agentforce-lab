"""
Phase 2: Generate External Data (Sources Outside Salesforce CRM)
================================================================

D360 Concept: These represent data that lives OUTSIDE Salesforce — the kind of
data that makes D360 valuable. Without D360, this data stays siloed. With D360,
it gets unified with CRM data through identity resolution.

Key change from v1: Web analytics and product usage are now INDIVIDUAL-LEVEL
(keyed by user_email), not company-level. This is what makes Identity Resolution
work — IR matches people, not companies.

We generate 3 external data sources:

  1. Web Analytics      — individual website behavior (keyed by user email)
  2. Product Usage      — individual product telemetry (keyed by user email)
  3. Firmographic Data  — company enrichment data (keyed by domain, account-level)

Lesson Learned: Our first version keyed all external data by company domain only.
D360 Identity Resolution silently produced zero matches because it works at the
Individual level, not the Account level. No error, no warning — just empty results.
We had to manually link dozens of records in the Data Cloud UI before realizing
the root cause: external data must include individual-level identifiers (emails)
that match CRM Contact emails.
"""

import os
import json
import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(99)  # Different seed than Phase 1 for variety

# ---------------------------------------------------------------------------
# Load references from Phase 1
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE1_DIR = os.path.join(SCRIPT_DIR, "..", "01-synthetic-data")
COMPANY_REF = os.path.join(PHASE1_DIR, "company_reference.json")
CONTACT_REF = os.path.join(PHASE1_DIR, "contact_reference.json")


def load_companies():
    """Load the company reference created by Phase 1."""
    if not os.path.exists(COMPANY_REF):
        print(f"❌ Company reference not found at {COMPANY_REF}")
        print("   Run Phase 1 first: cd ../01-synthetic-data && python generate_and_load.py")
        raise SystemExit(1)
    with open(COMPANY_REF) as f:
        companies = json.load(f)
    print(f"📂 Loaded {len(companies)} companies from Phase 1")
    return companies


def load_contacts():
    """Load the contact reference created by Phase 1."""
    if not os.path.exists(CONTACT_REF):
        print(f"❌ Contact reference not found at {CONTACT_REF}")
        print("   Run Phase 1 first: cd ../01-synthetic-data && python generate_and_load.py")
        raise SystemExit(1)
    with open(CONTACT_REF) as f:
        contacts = json.load(f)
    print(f"📂 Loaded {len(contacts)} contacts from Phase 1")
    return contacts


# ---------------------------------------------------------------------------
# Role-based inclusion logic
# ---------------------------------------------------------------------------

# Roles excluded from web analytics (these people don't browse the product website)
WEB_EXCLUDED_ROLES = {"VP of Sales", "Head of Customer Success"}

# Roles excluded from product usage (these people don't log into the product)
PRODUCT_EXCLUDED_ROLES = {"VP of Sales", "Head of Customer Success", "Director of Product"}

# VP of Engineering has 50% chance of product usage (some VPs still code)
PRODUCT_MAYBE_ROLES = {"VP of Engineering"}


def _include_in_web(contact):
    """Determine if a contact should appear in web analytics."""
    return contact["title"] not in WEB_EXCLUDED_ROLES


def _include_in_product(contact):
    """Determine if a contact should appear in product usage."""
    if contact["title"] in PRODUCT_EXCLUDED_ROLES:
        return False
    if contact["title"] in PRODUCT_MAYBE_ROLES:
        return random.random() < 0.5
    return True


# ---------------------------------------------------------------------------
# Table 1: Web Analytics (Individual-Level)
# ---------------------------------------------------------------------------

def generate_web_analytics(contacts):
    """
    Generate web analytics data at the INDIVIDUAL level.

    Each row represents one person's website activity, keyed by their email.
    This email matches the CRM Contact email — that's how D360 Identity
    Resolution links web behavior to CRM records.

    ~80% coverage: role-based exclusions (VP of Sales, Head of CS don't browse)
    plus 5 random additional exclusions to simulate incomplete tracking.
    """
    today = datetime.now()

    # Filter by role, then exclude 5 more randomly
    eligible = [c for c in contacts if _include_in_web(c)]
    if len(eligible) > 5:
        excluded_indices = set(random.sample(range(len(eligible)), 5))
        eligible = [c for i, c in enumerate(eligible) if i not in excluded_indices]

    excluded_count = len(contacts) - len(eligible)
    print(f"   ℹ️  {excluded_count} contacts excluded from web analytics")
    print(f"      (role-based + 5 random = simulates incomplete tracking)")

    # Industry engagement multipliers
    industry_multiplier = {
        "Technology": 1.5,
        "Financial Services": 1.3,
        "Healthcare": 1.0,
        "Retail": 1.1,
        "Manufacturing": 0.8,
    }

    rows = []
    for contact in eligible:
        # Look up industry from domain — use company reference if available
        multiplier = 1.0  # default
        base_views = random.randint(20, 300)
        page_views = int(base_views * multiplier)

        # Role-based behavior: technical roles view more product pages
        is_technical = contact["title"] in {
            "CTO", "VP of Engineering", "Head of Data",
            "Data Engineer", "Solutions Architect", "IT Director",
        }
        product_pages = random.randint(5, 15) if is_technical else random.randint(1, 8)
        demo_visits = random.randint(1, 5) if is_technical else random.randint(0, 2)

        rows.append({
            "user_email": contact["email"],
            "company_domain": contact["domain"],
            "page_views_30d": page_views,
            "product_pages_viewed": product_pages,
            "demo_page_visits": demo_visits,
            "avg_session_minutes": round(random.uniform(1.5, 12.0), 1),
            "last_visit_date": (today - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(rows)
    print(f"   → Generated {len(df)} web analytics records (individual-level)")
    return df


# ---------------------------------------------------------------------------
# Table 2: Product Usage / Telemetry (Individual-Level)
# ---------------------------------------------------------------------------

def generate_product_usage(contacts, companies):
    """
    Generate product usage telemetry at the INDIVIDUAL level.

    Each row represents one person's product usage, keyed by email.
    The account_id_external (EXT-XXXXX) is per-company, not per-person —
    it represents the company's account in the external product system.

    ~70% coverage: non-technical roles excluded (they don't log in).
    """
    today = datetime.now()

    # Build company lookup for EXT IDs and health status
    company_ext_ids = {}
    company_health = {}
    for company in companies:
        ext_id = f"EXT-{random.randint(10000, 99999)}"
        company_ext_ids[company["domain"]] = ext_id
        company_health[company["domain"]] = random.random() > 0.3  # 70% healthy

    eligible = [c for c in contacts if _include_in_product(c)]
    excluded_count = len(contacts) - len(eligible)
    print(f"   ℹ️  {excluded_count} contacts excluded from product usage")
    print(f"      (non-technical roles don't log into the product)")

    rows = []
    for contact in eligible:
        domain = contact["domain"]
        is_healthy = company_health.get(domain, True)
        ext_id = company_ext_ids.get(domain, f"EXT-{random.randint(10000, 99999)}")

        # Company-wide health drives individual metrics
        if is_healthy:
            feature_score = random.randint(60, 95)
            api_calls = random.randint(500, 5000)  # Per-user API calls
            days_since_login = random.randint(0, 7)
        else:
            feature_score = random.randint(15, 45)
            api_calls = random.randint(10, 300)
            days_since_login = random.randint(14, 60)

        # Count active users at this company (for the per-company metric)
        active_at_company = sum(
            1 for c in eligible if c["domain"] == domain
        )

        rows.append({
            "user_email": contact["email"],
            "company_domain": domain,
            "account_id_external": ext_id,
            "feature_adoption_score": feature_score,
            "api_calls_30d": api_calls,
            "active_users": active_at_company,
            "last_login_date": (today - timedelta(days=days_since_login)).strftime("%Y-%m-%d"),
            "data_volume_gb": round(random.uniform(0.5, 50.0), 1),
        })

    df = pd.DataFrame(rows)
    print(f"   → Generated {len(df)} product usage records (individual-level)")
    return df


# ---------------------------------------------------------------------------
# Table 3: Firmographic Enrichment (Account-Level — unchanged concept)
# ---------------------------------------------------------------------------

def generate_firmographic_data(companies):
    """
    Generate firmographic enrichment data (like ZoomInfo, Clearbit).

    This stays at the ACCOUNT level — firmographic data describes companies,
    not individuals. In D360, this links to the Account DMO via domain field
    (DMO relationship), NOT through Identity Resolution.

    This teaches the second integration pattern: IR handles people,
    DMO relationships handle companies.
    """
    funding_stages = ["Seed", "Series A", "Series B", "Series C", "Growth", "Public", "Private"]

    tech_stacks = [
        "AWS, Python, PostgreSQL",
        "GCP, Java, BigQuery",
        "Azure, .NET, SQL Server",
        "AWS, Node.js, DynamoDB",
        "Multi-cloud, Python, Snowflake",
        "AWS, Scala, Spark, Delta Lake",
        "GCP, Go, Spanner",
        "Azure, Python, Databricks",
        "AWS, React, MongoDB",
        "On-prem, Java, Oracle",
    ]

    rows = []
    for company in companies:
        # ~20% name variations to test fuzzy matching
        name = company["name"]
        if random.random() < 0.2:
            variations = [
                name + " Inc.",
                name + " LLC",
                name.upper(),
                name.replace(" ", "  "),  # Double space typo
            ]
            name = random.choice(variations)

        base_revenue = company["employees"] * random.randint(150000, 250000)

        rows.append({
            "company_name": name,
            "domain": company["domain"],
            "employee_count": company["employees"] + random.randint(-20, 50),
            "annual_revenue_estimate": base_revenue,
            "funding_stage": random.choice(funding_stages),
            "tech_stack_tags": random.choice(tech_stacks),
        })

    df = pd.DataFrame(rows)
    print(f"   → Generated {len(df)} firmographic records (account-level)")
    return df


# ---------------------------------------------------------------------------
# Export to CSV
# ---------------------------------------------------------------------------

def export_csvs(web_analytics, product_usage, firmographic):
    """Export all tables as CSV files for D360 Data Stream ingestion."""
    output_dir = os.path.join(SCRIPT_DIR, "csv_exports")
    os.makedirs(output_dir, exist_ok=True)

    files = {
        "web_analytics.csv": web_analytics,
        "product_usage.csv": product_usage,
        "firmographic_enrichment.csv": firmographic,
    }

    for filename, df in files.items():
        path = os.path.join(output_dir, filename)
        df.to_csv(path, index=False)
        print(f"   📄 {filename} ({len(df)} rows)")

    print(f"\n   Files saved to: {output_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Phase 2: External Data Generation")
    print("=" * 70)
    print()
    print("D360 Context: This is the data that lives OUTSIDE Salesforce.")
    print("Without D360, these signals are invisible to your CRM users.")
    print("With D360, they're unified with CRM data via identity resolution.")
    print()

    # Load Phase 1 references
    companies = load_companies()
    contacts = load_contacts()

    # Generate all three external data sources
    print("\n📊 Generating Web Analytics (individual-level)...")
    web_analytics = generate_web_analytics(contacts)

    print("\n📊 Generating Product Usage (individual-level)...")
    product_usage = generate_product_usage(contacts, companies)

    print("\n📊 Generating Firmographic Enrichment (account-level)...")
    firmographic = generate_firmographic_data(companies)

    # Export CSVs
    print("\n💾 Exporting CSVs for D360 Data Cloud...")
    export_csvs(web_analytics, product_usage, firmographic)

    # Summary
    print()
    print("=" * 70)
    print("✅ Phase 2 Complete!")
    print("=" * 70)
    print()
    print("What was created:")
    print(f"  • Web Analytics:   {len(web_analytics)} records (individual-level, keyed by user_email)")
    print(f"  • Product Usage:   {len(product_usage)} records (individual-level, keyed by user_email)")
    print(f"  • Firmographic:    {len(firmographic)} records (account-level, keyed by domain)")
    print()
    print("Data quality challenges (intentional):")
    print(f"  → Web analytics covers ~{len(web_analytics)}/{len(contacts)} contacts ({100*len(web_analytics)//len(contacts)}%)")
    print(f"  → Product usage covers ~{len(product_usage)}/{len(contacts)} contacts ({100*len(product_usage)//len(contacts)}%)")
    print("  → Product usage uses external IDs (EXT-XXXXX), not Salesforce IDs")
    print("  → Firmographic data has name variations (~20% of companies)")
    print()
    print("Identity Resolution will match on:")
    print("  → user_email (web analytics + product usage) ↔ Contact email (CRM)")
    print("  → domain (firmographic) ↔ Account website (CRM) — via DMO relationship")
    print()
    print("Next: Phase 3 — Configure D360 (data streams, DMOs, identity resolution)")


if __name__ == "__main__":
    main()
