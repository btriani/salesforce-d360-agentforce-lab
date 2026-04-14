# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 2: External Data — Delta Tables for D360 Zero Copy
# MAGIC
# MAGIC **D360 Concept:** These Delta tables represent external data sources outside Salesforce.
# MAGIC D360 queries them directly via **Zero Copy Federation** — no data movement needed.
# MAGIC
# MAGIC **Key change from v1:** Web analytics and product usage are now **individual-level**
# MAGIC (keyed by `user_email`), not company-level. This is what makes Identity Resolution
# MAGIC work — IR matches people across sources via Contact Point Email.
# MAGIC
# MAGIC **What this notebook creates:**
# MAGIC 1. `web_analytics` — individual website behavior (keyed by user email)
# MAGIC 2. `product_usage` — individual product telemetry (keyed by user email)
# MAGIC 3. `firmographic_enrichment` — company enrichment data (keyed by domain, account-level)
# MAGIC
# MAGIC **Import instructions:** Upload this .py file to your Databricks workspace:
# MAGIC Workspace → Import → select this file → Run All
# MAGIC
# MAGIC > **Lesson Learned:** Our first version keyed all external data by company domain only.
# MAGIC > D360 Identity Resolution silently produced zero matches because IR works at the
# MAGIC > Individual level, not the Account level. External data must include individual-level
# MAGIC > identifiers (emails) that match CRM Contact emails.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import random
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.types import *

random.seed(99)

CATALOG = "workspace"
SCHEMA = "d360_lab"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"USE {CATALOG}.{SCHEMA}")

print(f"Using schema: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference Data
# MAGIC
# MAGIC Companies and contacts from Phase 1 CRM data. Embedded here so the notebook
# MAGIC is self-contained (no file dependencies). These must match exactly what was
# MAGIC loaded into Salesforce.

# COMMAND ----------

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

# Contacts: generated with Faker.seed(42) in Phase 1.
# For the notebook to be self-contained, load contact_reference.json from the
# local script output, or paste the contact list here after running Phase 1.
# The generate_external_data.py script handles this automatically via JSON.
#
# For this notebook, we read the CSV exports generated by the local script.
# Upload csv_exports/ to a Databricks volume or DBFS before running.

print(f"Loaded {len(COMPANIES)} companies")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option A: Load from CSV exports (recommended)
# MAGIC
# MAGIC Upload the CSVs generated by `generate_external_data.py` to a Databricks volume,
# MAGIC then read them as DataFrames and save as Delta tables.

# COMMAND ----------

# Adjust this path to where you uploaded the CSVs
CSV_VOLUME_PATH = "/Volumes/workspace/d360_lab/csv_uploads"

try:
    df_web = spark.read.csv(f"{CSV_VOLUME_PATH}/web_analytics.csv", header=True, inferSchema=True)
    df_usage = spark.read.csv(f"{CSV_VOLUME_PATH}/product_usage.csv", header=True, inferSchema=True)
    df_firmo = spark.read.csv(f"{CSV_VOLUME_PATH}/firmographic_enrichment.csv", header=True, inferSchema=True)

    df_web.write.mode("overwrite").saveAsTable("web_analytics")
    df_usage.write.mode("overwrite").saveAsTable("product_usage")
    df_firmo.write.mode("overwrite").saveAsTable("firmographic_enrichment")

    print(f"✅ web_analytics: {df_web.count()} rows (individual-level, keyed by user_email)")
    print(f"✅ product_usage: {df_usage.count()} rows (individual-level, keyed by user_email)")
    print(f"✅ firmographic_enrichment: {df_firmo.count()} rows (account-level, keyed by domain)")

except Exception as e:
    print(f"⚠️  CSV load failed: {e}")
    print(f"   Make sure CSVs are uploaded to {CSV_VOLUME_PATH}")
    print(f"   Or use Option B below to generate data inline.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Option B: Generate inline (fallback)
# MAGIC
# MAGIC If you can't upload CSVs, this generates the firmographic data inline.
# MAGIC Web analytics and product usage require contact data from Phase 1 —
# MAGIC use the CSV upload for those.

# COMMAND ----------

# Firmographic can be generated inline since it's account-level
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
        name, company["domain"],
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

df_firmo_inline = spark.createDataFrame(firmo_rows, schema=firmo_schema)
# Uncomment to save (only if Option A didn't run):
# df_firmo_inline.write.mode("overwrite").saveAsTable("firmographic_enrichment")
print(f"Firmographic (inline): {df_firmo_inline.count()} rows")
display(df_firmo_inline)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Three Delta tables in `workspace.d360_lab`:
# MAGIC
# MAGIC | Table | Rows | Level | Key | D360 Integration |
# MAGIC |-------|------|-------|-----|-----------------|
# MAGIC | `web_analytics` | ~44 | Individual | `user_email` | IR via Contact Point Email |
# MAGIC | `product_usage` | ~38 | Individual | `user_email` | IR via Contact Point Email |
# MAGIC | `firmographic_enrichment` | 25 | Account | `domain` | DMO relationship to Account |
# MAGIC
# MAGIC **Identity Resolution path (individual-level):**
# MAGIC `user_email` → Contact Point Email DMO → match with CRM Contact email → Unified Individual
# MAGIC
# MAGIC **DMO relationship path (account-level):**
# MAGIC `domain` → Firmographic DMO → relationship field → Account DMO
# MAGIC
# MAGIC **Next:** Phase 3 — Configure D360 Data Cloud (data streams, DMOs, IR, insights, segments)

# COMMAND ----------

spark.sql("SHOW TABLES").display()
