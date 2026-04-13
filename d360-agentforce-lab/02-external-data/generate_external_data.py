"""
Phase 2: Generate External Data (Sources Outside Salesforce CRM)
================================================================

D360 Concept: These represent data that lives OUTSIDE Salesforce — the kind of
data that makes D360 valuable. Without D360, this data stays siloed in separate
systems. With D360, it gets ingested, mapped to DMOs, and unified with CRM data
through identity resolution.

We generate 3 external data sources:

  1. Web Analytics      — website visitor behavior (matched by company domain)
  2. Product Usage      — product telemetry (matched by a DIFFERENT external ID)
  3. Firmographic Data  — company enrichment data (matched by company name/domain)

Key design decisions for identity resolution testing:
  - ~80% of companies appear in web analytics (some gaps → tests partial matching)
  - Product Usage uses a different ID format (EXT-XXXX) instead of Salesforce IDs
    → demonstrates WHY identity resolution is needed
  - Firmographic data has slight name variations (e.g., "Inc" vs "Inc.")
    → tests fuzzy matching capabilities

Output: 3 CSV files ready for D360 Data Stream ingestion + the same data
embedded in the Databricks notebook for Delta table creation.
"""

import os
import json
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(99)  # Different seed than Phase 1 for variety
random.seed(99)

# ---------------------------------------------------------------------------
# Load company reference from Phase 1
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE1_DIR = os.path.join(SCRIPT_DIR, "..", "01-synthetic-data")
REFERENCE_FILE = os.path.join(PHASE1_DIR, "company_reference.json")

def load_companies():
    """Load the company reference created by Phase 1."""
    if not os.path.exists(REFERENCE_FILE):
        print(f"❌ Company reference not found at {REFERENCE_FILE}")
        print("   Run Phase 1 first: cd ../01-synthetic-data && python generate_and_load.py")
        raise SystemExit(1)

    with open(REFERENCE_FILE) as f:
        companies = json.load(f)
    print(f"📂 Loaded {len(companies)} companies from Phase 1 reference")
    return companies


# ---------------------------------------------------------------------------
# Table 1: Web Analytics
# ---------------------------------------------------------------------------

def generate_web_analytics(companies):
    """
    Generate web analytics data simulating website visitor behavior.

    D360 Concept: This data typically comes from tools like Google Analytics,
    Mixpanel, or a custom data warehouse. In D360, it's ingested via a
    Data Stream (file upload, S3 connector, or Zero Copy from Databricks).

    Identity Resolution: We use 'company_domain' as the matching key.
    D360 will match this against Contact email domains from the CRM
    (e.g., jane.doe@apexfintech.com → apexfintech.com).

    ~80% coverage: 5 companies are intentionally excluded to demonstrate
    that identity resolution handles incomplete data gracefully.
    """
    today = datetime.now()

    # Exclude ~20% of companies (5 out of 25) to test partial matching
    excluded_indices = random.sample(range(len(companies)), 5)
    excluded_names = [companies[i]["name"] for i in excluded_indices]
    print(f"   ℹ️  Excluded from web analytics (tests partial matching):")
    for name in excluded_names:
        print(f"      - {name}")

    rows = []
    for i, company in enumerate(companies):
        if i in excluded_indices:
            continue

        # Generate realistic web engagement signals
        # Higher engagement for tech/fintech companies (they research more online)
        industry_multiplier = {
            "Technology": 1.5,
            "Financial Services": 1.3,
            "Healthcare": 1.0,
            "Retail": 1.1,
            "Manufacturing": 0.8,
        }.get(company["industry"], 1.0)

        base_views = random.randint(50, 500)
        page_views = int(base_views * industry_multiplier)

        rows.append({
            "company_domain": company["domain"],
            "page_views_30d": page_views,
            "product_pages_viewed": random.randint(2, 15),
            "demo_page_visits": random.randint(0, 5),
            "avg_session_minutes": round(random.uniform(1.5, 12.0), 1),
            "last_visit_date": (today - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(rows)
    print(f"   → Generated {len(df)} web analytics records")
    return df


# ---------------------------------------------------------------------------
# Table 2: Product Usage / Telemetry
# ---------------------------------------------------------------------------

def generate_product_usage(companies):
    """
    Generate product usage telemetry data.

    D360 Concept: This simulates data from your product's backend — API logs,
    feature usage metrics, login activity. This is often the most valuable
    external data for D360 because it reveals actual customer behavior
    (vs. CRM data which is sales-reported).

    Identity Resolution Challenge: We deliberately use a DIFFERENT ID format
    (EXT-XXXX) instead of Salesforce Account IDs. This is realistic — your
    product database doesn't know Salesforce IDs. D360's identity resolution
    must reconcile these different identifiers.

    Interview talking point: "External systems rarely share the same primary
    key as Salesforce. D360's identity resolution handles this by matching
    on secondary attributes like domain, email, or company name."
    """
    today = datetime.now()
    rows = []

    for company in companies:
        # Generate an external ID that looks nothing like a Salesforce ID
        # This is the whole point — different systems, different IDs
        external_id = f"EXT-{random.randint(10000, 99999)}"

        # Usage signals — mix of healthy and unhealthy patterns
        is_healthy = random.random() > 0.3  # 70% healthy usage

        if is_healthy:
            feature_score = random.randint(60, 95)
            api_calls = random.randint(5000, 50000)
            active_users = random.randint(10, company["employees"] // 5)
            days_since_login = random.randint(0, 7)
        else:
            feature_score = random.randint(15, 45)
            api_calls = random.randint(100, 3000)
            active_users = random.randint(1, 5)
            days_since_login = random.randint(14, 60)

        rows.append({
            "account_id_external": external_id,
            "company_name": company["name"],  # Secondary match key for identity resolution
            "company_domain": company["domain"],  # Another match key
            "feature_adoption_score": feature_score,
            "api_calls_30d": api_calls,
            "active_users": active_users,
            "last_login_date": (today - timedelta(days=days_since_login)).strftime("%Y-%m-%d"),
            "data_volume_gb": round(random.uniform(0.5, 50.0), 1),
        })

    df = pd.DataFrame(rows)
    print(f"   → Generated {len(df)} product usage records")
    return df


# ---------------------------------------------------------------------------
# Table 3: Firmographic Enrichment
# ---------------------------------------------------------------------------

def generate_firmographic_data(companies):
    """
    Generate firmographic enrichment data (like ZoomInfo, Clearbit, etc.).

    D360 Concept: Enrichment data adds context that neither CRM nor product
    usage captures — funding stage, tech stack, precise revenue estimates.
    In D360, this maps to custom DMOs or extends the Account DMO.

    Identity Resolution: Uses company_name and domain as match keys.
    Some names have slight variations (e.g., extra "Inc." or different casing)
    to test fuzzy matching.
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
        # Introduce slight name variations for ~20% of companies
        # This tests D360's fuzzy matching in identity resolution
        name = company["name"]
        if random.random() < 0.2:
            variations = [
                name + " Inc.",
                name + " LLC",
                name.upper(),
                name.replace(" ", "  "),  # Double space typo
            ]
            name = random.choice(variations)

        # Revenue estimate with some noise vs. what's in CRM
        # (external enrichment data is never perfectly accurate)
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
    print(f"   → Generated {len(df)} firmographic records")
    return df


# ---------------------------------------------------------------------------
# Export to CSV
# ---------------------------------------------------------------------------

def export_csvs(web_analytics, product_usage, firmographic):
    """
    Export all tables as CSV files.

    These CSVs are what you upload to D360 Data Cloud as Data Streams.
    In a production environment, you'd use an S3 connector or Zero Copy
    instead of file uploads — but for a Dev Edition lab, CSV upload works.
    """
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
    return output_dir


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
    print("With D360, they're unified with CRM data via identity resolution")
    print("and become available to Agentforce agents.")
    print()

    # Load Phase 1 company reference
    companies = load_companies()

    # Generate all three external data sources
    print("\n📊 Generating Web Analytics...")
    web_analytics = generate_web_analytics(companies)

    print("\n📊 Generating Product Usage Telemetry...")
    product_usage = generate_product_usage(companies)

    print("\n📊 Generating Firmographic Enrichment...")
    firmographic = generate_firmographic_data(companies)

    # Export CSVs for D360 ingestion
    print("\n💾 Exporting CSVs for D360 Data Cloud upload...")
    export_csvs(web_analytics, product_usage, firmographic)

    # Summary
    print()
    print("=" * 70)
    print("✅ Phase 2 Complete!")
    print("=" * 70)
    print()
    print("What was created:")
    print(f"  • Web Analytics:   {len(web_analytics)} records (matched by company_domain)")
    print(f"  • Product Usage:   {len(product_usage)} records (uses EXT-XXXXX IDs — not SF IDs)")
    print(f"  • Firmographic:    {len(firmographic)} records (some name variations for fuzzy matching)")
    print()
    print("Identity Resolution highlights:")
    print("  → Web analytics covers ~80% of accounts (5 intentionally missing)")
    print("  → Product usage uses external IDs (EXT-XXXXX), not Salesforce IDs")
    print("  → Firmographic data has slight name variations (~20% of companies)")
    print("  → These mismatches are INTENTIONAL — they test D360 identity resolution")
    print()
    print("D360 Interview Talking Points:")
    print("  → 'External data is where D360 creates real value — it unifies signals'")
    print("  →   'that are invisible if you only look at CRM data'")
    print("  → 'I deliberately used different ID formats across sources to test'")
    print("  →   'identity resolution — just like real-world data integration'")
    print("  → 'The ~80% coverage in web analytics shows how D360 handles'")
    print("  →   'incomplete data — not every source covers every account'")
    print()
    print("Next steps:")
    print("  1. Upload CSVs from csv_exports/ to D360 Data Cloud as Data Streams")
    print("  2. (Optional) Run the Databricks notebook to create Delta tables")
    print("  3. Proceed to Phase 3: Configure D360 (identity resolution, insights)")


if __name__ == "__main__":
    main()
