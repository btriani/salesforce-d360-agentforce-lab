# Salesforce Bug Report Draft — Custom DMO API HTTP 500 on Multi-Field Payload

This document is a ready-to-file bug report for the Data Cloud Connect REST API custom DMO creation endpoint.

## Where to File

`issues.salesforce.com` (now `help.salesforce.com/s/issues`) is a **read-only portal** that shows issues Salesforce has already acknowledged. It does not accept new submissions. Developer Edition orgs do not include support case access by default, so the realistic channels for this report are:

1. **Trailblazer Community — Data Cloud group** (recommended): https://trailhead.salesforce.com/trailblazer-community/topics/datacloud — public, searchable, monitored by Salesforce engineers. A copy-paste-ready post is provided in the "Trailblazer Community Post" section below.
2. **Salesforce Developer Forums — Data Cloud category**: https://developer.salesforce.com/forums
3. **Log a Support Case** (only if your Salesforce account has paid support): [Log a Support Case for Data Cloud](https://help.salesforce.com/s/articleView?id=001461744&language=en_US&type=1)

---

## Title

Custom DMO creation via `POST /services/data/v64.0/ssot/data-model-objects` returns HTTP 500 `UNKNOWN_EXCEPTION` for any payload with two or more `fields` entries (Developer Edition with Data Cloud enabled)

## Summary

The Data Cloud Connect REST API endpoint for creating a custom Data Model Object (DMO) succeeds with a single-field payload (HTTP 201) but returns HTTP 500 `UNKNOWN_EXCEPTION` for the smallest multi-field payload (two `Text` fields). The published API specification explicitly supports multi-field `fields` arrays (available since v60.0), and the sample payload in the Salesforce Developers documentation uses a multi-element `fields` array. The failure is not one of the documented 400 validation errors and does not match any published Developer Edition limit.

## Affected Environment

- **Edition:** Developer Edition with Data Cloud (Data 360) enabled
- **Org Instance:** `orgfarm-ae1d59d1bd-dev-ed.develop.my.salesforce.com`
- **API Version:** v64.0 (reproduced on the latest publicly available `/services/data/vNN.0/ssot/data-model-objects`)
- **Connect API Endpoint:** `POST /services/data/v64.0/ssot/data-model-objects`
- **Authentication:** Standard bearer token obtained from `sf org display --target-org <alias> --json`
- **Date reproduced:** 2026-04-14

## Steps to Reproduce

1. Authenticate against a Developer Edition org with Data Cloud enabled via the Salesforce CLI.
2. Obtain a bearer token from `sf org display --target-org <alias> --json`.
3. Send a `POST /services/data/v64.0/ssot/data-model-objects` request with a **single-field** payload. Observe HTTP 201.
4. Send the same request with the **smallest possible multi-field** payload (primary key plus one additional `Text` field). Observe HTTP 500 `UNKNOWN_EXCEPTION`.

### Working Payload (HTTP 201)

```json
{
  "name": "Probe_Minimal_SingleField",
  "label": "Probe Minimal Single Field",
  "category": "Profile",
  "fields": [
    {
      "name": "probe_key",
      "label": "Probe Key",
      "dataType": "Text",
      "isPrimaryKey": true
    }
  ]
}
```

**Response:** `HTTP 201 Created`. The resulting DMO is visible via `GET /services/data/v64.0/ssot/data-model-objects/Probe_Minimal_SingleField__dlm`, and the system also auto-injects `DataSource__c`, `DataSourceObject__c`, `InternalOrganization__c`, and `KQ_probe_key__c`.

### Failing Payload (HTTP 500)

```json
{
  "name": "Probe_TwoFields",
  "label": "Probe Two Fields",
  "category": "Profile",
  "fields": [
    {
      "name": "probe_key",
      "label": "Probe Key",
      "dataType": "Text",
      "isPrimaryKey": true
    },
    {
      "name": "probe_text",
      "label": "Probe Text",
      "dataType": "Text"
    }
  ]
}
```

**Response:**

```json
[
  {
    "errorCode": "UNKNOWN_EXCEPTION",
    "message": "An unexpected error occurred. Please include this ErrorId if you contact support: 1169266788-367379 (-2106090025)"
  }
]
```

This reproduces consistently across multiple runs with different names and labels.

## Expected Behavior

Per the Salesforce Developers [Data 360 Connect API reference — Create data model object](https://developer.salesforce.com/docs/data/connectapi/references/spec) (Available Version: 61.0):

- The `fields` parameter is documented as `Array of objects (Data Object Field Input) — Fields in the data object`
- The sample payload in the docs includes multiple field entries
- The documented failure modes are HTTP 400 for invalid input / duplicate developer name
- HTTP 500 is not a documented response for this endpoint

The request with a two-field payload should succeed with HTTP 201, returning a DMO that has both user-defined fields plus the auto-injected system fields.

## Actual Behavior

- Single-field payload: succeeds with HTTP 201 (expected)
- Two-or-more-field payload: fails with HTTP 500 `UNKNOWN_EXCEPTION` and an opaque ErrorId
- No hint in the response indicates a validation problem, a limit, or an authorization issue

## Why This Matters

This prevents any programmatic creation of custom DMOs that mirror realistic external Data Lake Object (DLO) schemas. For example, a Web Analytics DLO with 6 to 10 business fields cannot be mirrored to a custom DMO via the Connect REST API in Developer Edition. Downstream work blocked by this includes:

- Mapping external DLOs to custom DMOs for Identity Resolution
- Building Calculated Insights that JOIN external data (CIs can only reference DMOs, not DLOs directly)
- Deploying Segments that depend on those Calculated Insights
- Any "Data 360 as code" or DevOps flow that relies on `/ssot/data-model-objects` for multi-field custom DMO creation

## What We Tried / Ruled Out

| Hypothesis | Verified? | Evidence |
|-----------|-----------|----------|
| It is a field-count limit on Dev Edition | No — per-DMO field limit is documented as 800 per type / 1,050 total, with no Dev-Edition-specific reduction | [Customer Data Platform Limits and Guidelines](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines_cdp.htm&language=en_US&type=5) |
| It is a data-type issue (Number or Date) | No — the two-Text-field probe also fails with HTTP 500, identically to Number and Date payloads | See evidence artifacts below |
| It is a published validation error (HTTP 400) | No — the response is 500 with `UNKNOWN_EXCEPTION`, not the documented 400 validation responses | [Connect API reference](https://developer.salesforce.com/docs/data/connectapi/references/spec) |
| It is a duplicate-name collision | No — each probe uses a unique timestamped name and passes an existence preflight before POSTing | See evidence artifacts below |
| It is a known issue in the community | No — exhaustive searches of Salesforce Known Issues, Trailblazer community, Stack Overflow, GitHub, and Salesforce Idea Exchange returned no matching report | — |
| It is a Developer Edition documented restriction | No — [Developer Edition Limits and Guidelines for Data 360](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm&language=en_US&type=5) lists only count-based limits (300 DMOs, 100 DLOs, 100 data streams, 25 active segments, 2 IR rulesets, 10 GB data, 1 data space) and does not restrict custom DMO field count or creation method | — |

## Evidence Artifacts

Raw request and response data from a live Developer Edition org on 2026-04-14, including the ErrorId from the failing response, are preserved in this repo:

- Successful single-field create: `d360-agentforce-lab/03-d360-config/artifacts/probe_create_custom_dmo-20260414T170126_843286Z.json`
- Failing two-Text-field create: `d360-agentforce-lab/03-d360-config/artifacts/probe_dmo_field_types_text_only-20260414T170132_026331Z.json`
- Failing external DMO specs (Web_Engagement, Product_Telemetry, Firmographic_Data): `d360-agentforce-lab/03-d360-config/artifacts/deploy_custom_dmos_summary-20260414T170144_344573Z.json`
- Summary matrix across probe variants: `d360-agentforce-lab/03-d360-config/artifacts/probe_dmo_field_types_summary-20260414T170132_814601Z.json`

Repository with full reproduction scripts: https://github.com/btriani/salesforce-d360-agentforce-lab

### Server-Side Error IDs to Share With Support

Salesforce support can look these up in platform logs:

- `1169266788-367379 (-2106090025)` — two-Text-field probe
- (Additional ErrorIds available in the artifacts above)

## Reproduction Script

From the linked repo:

```bash
# Authenticate once
sf org login web --alias my-dev-org

# Reproduce with the probe suite
./.venv/bin/python d360-agentforce-lab/03-d360-config/scripts/probes/probe_create_custom_dmo.py       # passes (single field)
./.venv/bin/python d360-agentforce-lab/03-d360-config/scripts/probes/probe_dmo_field_types.py         # fails starting at 2 fields
```

Evidence is written under `d360-agentforce-lab/03-d360-config/artifacts/` on every run.

## Workarounds Currently in Use

None is fully satisfactory for a programmatic deployment:

1. **Create from existing DLO via the Setup UI** ([documented path](https://help.salesforce.com/s/articleView?id=sf.c360_a_create_custom_dmo_from_existing.htm)). Works, but defeats the purpose of the Connect REST API and blocks any "config as code" workflow.
2. **SFDX / Metadata API via DevOps Data Kits**. Plausible but not validated for this specific use case in this org.
3. **Empirical**: create a DMO with a single field, then `PATCH` to add the remaining fields. Not documented and not officially supported.

## Request to Salesforce

1. Confirm whether this is a regression in Developer Edition or a broader platform bug.
2. If this is an intentional Developer Edition restriction, publish it on the [Developer Edition Limits and Guidelines for Data 360](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm&language=en_US&type=5) page. Today, nothing on that page hints at a field-count or creation-method restriction.
3. If this is a bug, fix the `POST /ssot/data-model-objects` endpoint to accept multi-field payloads as the API spec already documents, or return a specific HTTP 400 that identifies the precise unsupported input so that clients can adapt.

## Trailblazer Community Post

Copy and paste the block below into a new post in the [Data Cloud group on Trailblazer Community](https://trailhead.salesforce.com/trailblazer-community/topics/datacloud). Adjust the org details if needed.

---

**Title:** Data Cloud Connect API `POST /ssot/data-model-objects` returns HTTP 500 `UNKNOWN_EXCEPTION` for any multi-field custom DMO payload on Developer Edition

**Post body:**

Hi all — looking for confirmation from Salesforce engineering or anyone else seeing this.

**Environment**
- Developer Edition with Data Cloud (Data 360) enabled
- API v64.0
- Endpoint: `POST /services/data/v64.0/ssot/data-model-objects`
- Auth: bearer token from `sf org display --target-org <alias> --json`

**Observed behavior**
- Payload with **one** `Text` primary-key field: **HTTP 201 Created** (works)
- Payload with **two** `Text` fields (primary key + one more): **HTTP 500 `UNKNOWN_EXCEPTION`**

Response body of the failing call:
```json
[{"errorCode":"UNKNOWN_EXCEPTION","message":"An unexpected error occurred. Please include this ErrorId if you contact support: 1169266788-367379 (-2106090025)"}]
```

**Expected behavior**
The [Connect API spec](https://developer.salesforce.com/docs/data/connectapi/references/spec) documents `fields` as a multi-element array (Available Version: 61.0) and the sample payload in the docs uses multiple fields. Documented failure modes are HTTP 400 only.

**Ruled out**
- Field count: not a Dev Edition documented limit (the [Developer Edition Limits page](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm) lists count-based limits only, and the [CDP Limits page](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines_cdp.htm) sets per-DMO field limits at 800 per type / 1,050 total, org-wide)
- Data type: fails with two `Text` fields, no Number or Date involved
- Validation (HTTP 400): not triggered; server returns 500
- Duplicate name: probe uses a unique timestamped name with a preflight check
- Known Issue: no matching entry on `help.salesforce.com/s/issues`

**Reproduction**
Full reproduction scripts and artifacts: https://github.com/btriani/salesforce-d360-agentforce-lab (see `d360-agentforce-lab/03-d360-config/scripts/probes/` and `artifacts/`). Salesforce support ErrorId for log lookup: `1169266788-367379 (-2106090025)`.

**Questions**
1. Is this a known bug in Developer Edition, and if so where is it tracked?
2. If this is an intentional restriction, can it be added to the [Developer Edition Limits and Guidelines for Data 360](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm) page?
3. Is the [Create a Custom DMO from an Existing DLO](https://help.salesforce.com/s/articleView?id=sf.c360_a_create_custom_dmo_from_existing.htm) UI path the only supported workflow on Developer Edition right now?

Thanks!

---

## References

- [Developer Edition Limits and Guidelines for Data 360](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm&language=en_US&type=5)
- [Data 360 Limits and Guidelines](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines.htm&language=en_US)
- [Customer Data Platform Limits and Guidelines](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines_cdp.htm&language=en_US&type=5) (per-DMO field limits: 800 per type, 1,050 total)
- [Data 360 Connect REST API spec — `POST /ssot/data-model-objects`](https://developer.salesforce.com/docs/data/connectapi/references/spec)
- [Create a Custom DMO from an Existing DLO (UI path)](https://help.salesforce.com/s/articleView?id=sf.c360_a_create_custom_dmo_from_existing.htm)
- [REST API Status Codes and Error Responses — `UNKNOWN_EXCEPTION`](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/errorcodes.htm)
- [Salesforce Known Issues portal](https://help.salesforce.com/s/issues) (read-only; does not accept new submissions)
- [Trailblazer Community — Data Cloud group](https://trailhead.salesforce.com/trailblazer-community/topics/datacloud) (recommended submission channel for Developer Edition users)
- [Log a Support Case for Data Cloud](https://help.salesforce.com/s/articleView?id=001461744&language=en_US&type=1) (requires paid support plan)
