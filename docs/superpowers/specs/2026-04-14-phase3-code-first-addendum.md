# Spec Addendum: Phase 3 Code-First Restructure

**Parent spec:** `2026-04-14-d360-lab-rewrite-design.md`
**Date:** 2026-04-14
**Trigger:** 2 days blocked on UI-based Identity Resolution; Contact Point Email DMO not appearing for external DLOs in Dev Edition.

## Problem

The original Phase 3 design was UI-based step-by-step instructions. Running it exposed critical issues:

1. **Identity Resolution rulesets cannot be deployed via Metadata API** — only via Data Cloud Connect REST API
2. **Contact Point Email DMO behavior varies** by data space and source (appears for CRM DLOs, hidden for external Databricks DLOs in Dev Edition)
3. **Dozens of manual clicks** for field mapping, even with correct data model
4. **No reproducibility** — can't redeploy or version-control the configuration

## Decision

Rewrite Phase 3 as **code-first D360 deployment** using a hybrid approach:

| What | How | Why |
|------|-----|-----|
| Data Streams (Databricks) | Manual UI setup (one-time) | Requires Databricks connector OAuth; not fully scriptable |
| DLO→DMO field mappings | SFDX metadata XML (optional) OR UI review | Metadata API supports `ObjectSourceTargetMap` but CRM Contact DLO auto-maps via Sales Cloud bundle |
| **Identity Resolution ruleset** | **Python + Data Cloud Connect REST API** | **THE CRITICAL FIX** — not available via Metadata API at all |
| Calculated Insight (Health Score) | Python + REST API | Reliable, scriptable, SQL is version-controlled |
| Segments | Python + REST API | Same reasons |

## Key Design Changes from Original Spec

1. **IR uses Party Identification, not Contact Point Email**
   - Party Identification is more reliable for external data (exact match on stable IDs)
   - Contact Point Email has data space / Dev Edition visibility issues
   - Official Salesforce recommendation for multi-source IR (per Trailhead)

2. **Match rule strategy**
   - **Primary rule:** Exact match on Party Identification (user email as identification number)
   - **Fallback rule:** Normalized Email on Contact Point Email (for CRM side, where it works)

3. **Phase 3 README rewrite (Option B chosen)**
   - Current README is "theoretical / UI-based"
   - Rewrite to be code-first: concepts woven into actual deploy instructions
   - Preserve "Field Notes" section with expanded 2-day-wall lesson learned

## Deliverables

```
d360-agentforce-lab/03-d360-config/
├── README.md                              # REWRITTEN: code-first deploy guide
├── scripts/
│   ├── deploy_all.py                      # Orchestrator
│   ├── deploy_identity_resolution.py      # IR ruleset via Connect REST API
│   ├── deploy_calculated_insight.py       # Health Score CI via REST API
│   ├── deploy_segments.py                 # 3 segments via REST API
│   ├── verify_deployment.py               # Confirm everything deployed
│   └── requirements.txt
└── (existing content)
```

## Out of Scope for This Addendum

- Full SFDX Metadata API bundle for DLOs/DMOs/streams — the Metadata API coverage is incomplete and has gotchas (dataspace pre-creation, connector re-auth, dependency ordering). Stick to what's reliable: Python + REST API for the pieces that matter.
- Automated Databricks connector creation — requires OAuth handshake, not scriptable from this side.
- Agentforce agent deployment — that's Phase 4, handled separately.

## Success Criteria

1. Running `python deploy_all.py` successfully creates:
   - 1 Identity Resolution ruleset
   - 1 Calculated Insight (Health Score)
   - 3 Segments (At Risk, Healthy, Upsell Ready)
2. IR ruleset processes and produces unified individuals without manual UI intervention
3. Can delete the config and redeploy with a single command
4. README documents the full deploy workflow + preserves the "2-day wall" lesson learned
