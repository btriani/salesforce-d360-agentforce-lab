# Public API Notes

Concrete findings from the current `my-dev-org` investigation on 2026-04-14. These notes are grounded in the artifacts already checked into this repo and are meant to separate proven public surfaces from still-unresolved mapping work.

| Surface | Method | Status | Notes |
|---------|--------|--------|-------|
| `/services/data/v64.0/ssot/queryv2` | `POST` | Works for ad-hoc cross-source SQL | `verify_readiness.py` uses this surface to run the Health Score join across CRM DMOs plus external DLOs and requires at least 25 account rows. This proves queryability, not Calculated Insight compatibility. |
| `/services/data/v64.0/ssot/data-model-objects` | `POST` | Works for the smallest known payload | `artifacts/probe_create_custom_dmo-20260414T170126_843286Z.json` shows HTTP `201 Created` for a custom DMO with one `Text` primary key field. Salesforce also injects system fields like `DataSource__c` and a key qualifier field. |
| `/services/data/v64.0/ssot/data-model-objects` | `POST` | Fails for the next step up in realism | `artifacts/probe_dmo_field_types_text_only-20260414T170132_026331Z.json` shows HTTP `500 UNKNOWN_EXCEPTION` for a payload with just two `Text` fields. The cumulative `with_number` and `with_date` cases also fail in `probe_dmo_field_types_summary-20260414T170132_814601Z.json`. |
| `/services/data/v64.0/ssot/data-model-objects` | `POST` | Fails for the preserved external DMO specs | `artifacts/deploy_custom_dmos_summary-20260414T170144_344573Z.json` records HTTP `500` for `Web_Engagement__dlm`, `Product_Telemetry__dlm`, and `Firmographic_Data__dlm`, even after a preflight detail lookup. |
| `/services/data/v64.0/ssot/data-model-objects/{api_name}` | `GET` | Useful preflight for existence checks | `artifacts/deploy_custom_dmo_Web_Engagement-20260414T170142_855700Z.json` shows HTTP `404 ITEM_NOT_FOUND` for a missing DMO detail path. That response is useful evidence and should be treated as "not present," not as a probe failure. |
| `/services/data/v64.0/ssot/data-model-objects` | `GET` | Observed in live mapping-surface inventory | `artifacts/probe_mapping_surfaces_summary-20260414T171448_436518Z.json` returned HTTP `200` and a list of DMO definitions, so the collection surface is visible even though realistic creates still fail. |
| `/services/data/v64.0/ssot/data-lake-objects` | `GET` | Observed in live mapping-surface inventory | The same Task 4 inventory returned HTTP `200`, confirming that DLO collection metadata is exposed on a public surface in this org. |
| `/services/data/v64.0/ssot/data-streams` | `GET` | Observed in live mapping-surface inventory | The same Task 4 inventory returned HTTP `200`, which makes this a candidate discovery surface when correlating streams to downstream mapping work. |
| `/services/data/v64.0/ssot/data-mappings` | `GET` | Not found | The Task 4 inventory returned HTTP `404`, so this obvious mapping-named path is not exposed here. |
| `/services/data/v64.0/ssot/mappings` | `GET` | Not found | The Task 4 inventory returned HTTP `404`, and `probe_ui_replay-20260414T171435_691093Z.json` also recorded HTTP `404` for a replayed `POST` to a child path under `/ssot/mappings/...`. |

## Practical Boundaries

- Public Connect API evidence is strong for ad-hoc querying and for the smallest possible custom DMO create.
- The public custom DMO create surface becomes unstable immediately after the minimal one-field case in this org; the failures are server-side `UNKNOWN_EXCEPTION` responses, not client-side validation errors.
- DLO to DMO mapping remains unresolved on public surfaces. The Task 4 inventory narrowed the search: collection surfaces for DMOs, DLOs, and data streams are visible, while the two most obvious mapping-named paths return `404`.
- Metadata remains a plausible fallback for mapping work because the repo and design docs already note `ObjectSourceTargetMap` / DevOps Data Kits as a possible production-grade path, but that route has not been validated here yet.

## Status of the Multi-Field DMO 500: Undocumented Bug

Cross-checked against the [Developer Edition Limits and Guidelines for Data 360](https://help.salesforce.com/s/articleView?id=data.c360_a_limits_and_guidelines_dev_ed.htm&language=en_US&type=5), the [Data 360 Limits and Guidelines](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines.htm&language=en_US), the [Customer Data Platform Limits and Guidelines](https://help.salesforce.com/s/articleView?id=sf.c360_a_limits_and_guidelines_cdp.htm&language=en_US&type=5), and the [Connect API spec](https://developer.salesforce.com/docs/data/connectapi/references/spec).

Findings:

- Documented Developer Edition restrictions are all count-based: 300 DMOs, 100 DLOs, 100 data streams, 25 active segments, 2 IR rulesets, 10 GB data, 1 data space. No field-count or creation-method restriction.
- The documented per-DMO field limit is 800 per type / 1,050 total, applied org-wide, not Developer-Edition-specific.
- The Connect API spec documents the `fields` parameter as a multi-element array (Available Version: 61.0) and publishes a multi-field sample payload. The only documented failure modes are HTTP 400 validation errors.
- Nothing on the Salesforce Known Issues portal, Trailblazer community, Stack Overflow, GitHub, or Salesforce Idea Exchange matches this specific symptom.

Therefore, the HTTP 500 on multi-field custom DMO creation in Developer Edition is an **undocumented bug**, not a documented limitation. A ready-to-file bug report with reproduction steps, Salesforce support ErrorIds, and source citations is preserved at [bug-report-dmo-api-500.md](bug-report-dmo-api-500.md).
