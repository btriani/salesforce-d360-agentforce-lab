# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 2: External Data — Delta Tables for D360 Zero Copy
# MAGIC
# MAGIC **D360 Concept:** These Delta tables represent external data sources that live outside Salesforce.
# MAGIC In production, D360 can query these directly via **Zero Copy Federation** — no data movement needed.
# MAGIC Zero Copy had **341% YoY growth** and is a key D360 differentiator vs. traditional ETL.
# MAGIC
# MAGIC **What this notebook creates:**
# MAGIC 1. `web_analytics` — website visitor behavior (matched by company domain)
# MAGIC 2. `product_usage` — product telemetry (matched by external IDs, NOT Salesforce IDs)
# MAGIC 3. `firmographic_enrichment` — company enrichment data (fuzzy name matching)
# MAGIC
# MAGIC **Import instructions:** Upload this .py file to your Databricks workspace:
# MAGIC Workspace → Import → select this file → Run All

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import random
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.types import *

random.seed(99)

# Schema and catalog — adjust these to match your Databricks workspace
# For a trial workspace, the default catalog "main" and a new schema works fine
CATALOG = "workspace"
SCHEMA = "d360_lab"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"USE {CATALOG}.{SCHEMA}")

print(f"Using schema: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Company Reference Data
# MAGIC
# MAGIC These are the same companies loaded into Salesforce CRM in Phase 1.
# MAGIC We embed them here so the notebook is self-contained (no file dependencies).

# COMMAND ----------

# Matches Phase 1 companies exactly — same domains, industries, employee counts
COMPANIES = [
    {"name": "Apex Financial Technologies", "domain": "apexfintech.com", "industry": "Financial Services", "employees": 450},
    {"name": "Meridian Payments Group", "domain": "meridianpay.io", "industry": "Financial Services", "employees": 220},
    {"name": "Vaultline Digital Banking", "domain": "vaultline.com", "industry": "Financial Services", "employees": 380},
    {"name": "ClearEdge Capital Systems", "domain": "clearedgecap.com", "industry": "Financial Services", "employees": 150},
    {"name": "Fintrust Solutions", "domain": "fintrust.io", "industry": "Financial Services", "employees": 95},
    {"name": "Novus Health Analytics", "domain": "novushealth.com", "industry": "Healthcare", "employees": 600},
    {"name": "BioSync Medical Systems", "domain": "biosyncmed.com", "industry": "Healthcare", "employees": 340},
    {"name": "CarePoint Digital", "domain": "carepointdigital.com", "industry": "Healthcare", "employees": 180},
    {"name": "MedLattice Inc", "domain": "medlattice.com", "industry": "Healthcare", "employees": 520},
    {"name": "Helix Genomics Platform", "domain": "helixgenomics.io", "industry": "Healthcare", "employees": 275},
    {"name": "UrbanThread Retail", "domain": "urbanthread.com", "industry": "Retail", "employees": 1200},
    {"name": "Shopwise Commerce", "domain": "shopwise.io", "industry": "Retail", "employees": 310},
    {"name": "FreshCart Marketplace", "domain": "freshcart.com", "industry": "Retail", "employees": 480},
    {"name": "Lumenaire Brands", "domain": "lumenaire.com", "industry": "Retail", "employees": 200},
    {"name": "TrueNorth Outdoor Co", "domain": "truenorthoutdoor.com", "industry": "Retail", "employees": 160},
    {"name": "Forgewell Industries", "domain": "forgewell.com", "industry": "Manufacturing", "employees": 2100},
    {"name": "Steelvine Manufacturing", "domain": "steelvine.com", "industry": "Manufacturing", "employees": 850},
    {"name": "Precision Dynamics Corp", "domain": "precisiondynamics.com", "industry": "Manufacturing", "employees": 620},
    {"name": "Cascade Materials Group", "domain": "cascadematerials.com", "industry": "Manufacturing", "employees": 430},
    {"name": "Ironclad Components", "domain": "ironcladcomp.com", "industry": "Manufacturing", "employees": 290},
    {"name": "Neuralink Data Systems", "domain": "neuralinkdata.com", "industry": "Technology", "employees": 750},
    {"name": "CloudPeak Software", "domain": "cloudpeak.io", "industry": "Technology", "employees": 400},
    {"name": "DataVista Analytics", "domain": "datavista.com", "industry": "Technology", "employees": 190},
    {"name": "Quantum Edge Labs", "domain": "quantumedgelabs.com", "industry": "Technology", "employees": 130},
    {"name": "Synthetica AI", "domain": "synthetica.ai", "industry": "Technology", "employees": 85},
]

print(f"Loaded {len(COMPANIES)} companies")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 1: Web Analytics
# MAGIC
# MAGIC **D360 Identity Resolution Key:** `company_domain`
# MAGIC
# MAGIC D360 matches this against Contact email domains from CRM
# MAGIC (e.g., `jane.doe@apexfintech.com` → `apexfintech.com`).
# MAGIC
# MAGIC ~80% coverage: 5 companies excluded to test partial matching.

# COMMAND ----------

today = datetime.now()
excluded_indices = random.sample(range(len(COMPANIES)), 5)

web_rows = []
for i, company in enumerate(COMPANIES):
    if i in excluded_indices:
        continue
    multiplier = {"Technology": 1.5, "Financial Services": 1.3, "Healthcare": 1.0, "Retail": 1.1, "Manufacturing": 0.8}.get(company["industry"], 1.0)
    base_views = random.randint(50, 500)
    web_rows.append((
        company["domain"],
        int(base_views * multiplier),
        random.randint(2, 15),
        random.randint(0, 5),
        round(random.uniform(1.5, 12.0), 1),
        (today - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
    ))

web_schema = StructType([
    StructField("company_domain", StringType(), False),
    StructField("page_views_30d", IntegerType(), False),
    StructField("product_pages_viewed", IntegerType(), False),
    StructField("demo_page_visits", IntegerType(), False),
    StructField("avg_session_minutes", DoubleType(), False),
    StructField("last_visit_date", StringType(), False),
])

df_web = spark.createDataFrame(web_rows, schema=web_schema)
df_web.write.mode("overwrite").saveAsTable("web_analytics")

print(f"✅ web_analytics: {df_web.count()} rows")
display(df_web)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 2: Product Usage / Telemetry
# MAGIC
# MAGIC **Identity Resolution Challenge:** Uses `EXT-XXXXX` IDs instead of Salesforce IDs.
# MAGIC This is realistic — your product database doesn't know Salesforce Account IDs.
# MAGIC D360 resolves this by matching on secondary attributes (domain, company name).
# MAGIC
# MAGIC **Interview talking point:** "External systems rarely share the same primary key
# MAGIC as Salesforce. D360's identity resolution handles this by matching on secondary
# MAGIC attributes like domain, email, or company name."

# COMMAND ----------

usage_rows = []
for company in COMPANIES:
    external_id = f"EXT-{random.randint(10000, 99999)}"
    is_healthy = random.random() > 0.3

    if is_healthy:
        feature_score = random.randint(60, 95)
        api_calls = random.randint(5000, 50000)
        active_users = random.randint(10, max(11, company["employees"] // 5))
        days_since_login = random.randint(0, 7)
    else:
        feature_score = random.randint(15, 45)
        api_calls = random.randint(100, 3000)
        active_users = random.randint(1, 5)
        days_since_login = random.randint(14, 60)

    usage_rows.append((
        external_id,
        company["name"],
        company["domain"],
        feature_score,
        api_calls,
        active_users,
        (today - timedelta(days=days_since_login)).strftime("%Y-%m-%d"),
        round(random.uniform(0.5, 50.0), 1),
    ))

usage_schema = StructType([
    StructField("account_id_external", StringType(), False),
    StructField("company_name", StringType(), False),
    StructField("company_domain", StringType(), False),
    StructField("feature_adoption_score", IntegerType(), False),
    StructField("api_calls_30d", IntegerType(), False),
    StructField("active_users", IntegerType(), False),
    StructField("last_login_date", StringType(), False),
    StructField("data_volume_gb", DoubleType(), False),
])

df_usage = spark.createDataFrame(usage_rows, schema=usage_schema)
df_usage.write.mode("overwrite").saveAsTable("product_usage")

print(f"✅ product_usage: {df_usage.count()} rows")
display(df_usage)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 3: Firmographic Enrichment
# MAGIC
# MAGIC **D360 Concept:** Enrichment data from providers like ZoomInfo or Clearbit.
# MAGIC Adds context that neither CRM nor product usage captures — funding stage,
# MAGIC tech stack, precise revenue estimates.
# MAGIC
# MAGIC Some company names have slight variations (~20%) to test fuzzy matching
# MAGIC in identity resolution.

# COMMAND ----------

funding_stages = ["Seed", "Series A", "Series B", "Series C", "Growth", "Public", "Private"]
tech_stacks = [
    "AWS, Python, PostgreSQL", "GCP, Java, BigQuery", "Azure, .NET, SQL Server",
    "AWS, Node.js, DynamoDB", "Multi-cloud, Python, Snowflake", "AWS, Scala, Spark, Delta Lake",
    "GCP, Go, Spanner", "Azure, Python, Databricks", "AWS, React, MongoDB", "On-prem, Java, Oracle",
]

firmo_rows = []
for company in COMPANIES:
    name = company["name"]
    if random.random() < 0.2:
        name = random.choice([name + " Inc.", name + " LLC", name.upper(), name.replace(" ", "  ")])

    base_revenue = company["employees"] * random.randint(150000, 250000)
    firmo_rows.append((
        name,
        company["domain"],
        company["employees"] + random.randint(-20, 50),
        base_revenue,
        random.choice(funding_stages),
        random.choice(tech_stacks),
    ))

firmo_schema = StructType([
    StructField("company_name", StringType(), False),
    StructField("domain", StringType(), False),
    StructField("employee_count", IntegerType(), False),
    StructField("annual_revenue_estimate", LongType(), False),
    StructField("funding_stage", StringType(), False),
    StructField("tech_stack_tags", StringType(), False),
])

df_firmo = spark.createDataFrame(firmo_rows, schema=firmo_schema)
df_firmo.write.mode("overwrite").saveAsTable("firmographic_enrichment")

print(f"✅ firmographic_enrichment: {df_firmo.count()} rows")
display(df_firmo)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Three Delta tables created in `main.d360_lab`:
# MAGIC
# MAGIC | Table | Rows | Identity Resolution Key | D360 Concept |
# MAGIC |-------|------|------------------------|--------------|
# MAGIC | `web_analytics` | ~20 | `company_domain` | External behavioral data |
# MAGIC | `product_usage` | 25 | `account_id_external` (EXT-XXXXX) + `company_domain` | Product telemetry with foreign IDs |
# MAGIC | `firmographic_enrichment` | 25 | `company_name` + `domain` | Third-party enrichment |
# MAGIC
# MAGIC **Next:** In Phase 3, configure D360 Data Cloud to ingest these (via CSV upload or Zero Copy)
# MAGIC and set up identity resolution rules to match across all sources.

# COMMAND ----------

# Quick validation: show all tables
spark.sql("SHOW TABLES").display()
