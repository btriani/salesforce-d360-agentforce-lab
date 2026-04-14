# Internal Endpoints

No browser-captured mapping endpoint has been validated in this repo yet. This file is the working notebook for the next capture, and it now doubles as a parseable source for `scripts/probes/probe_ui_replay.py`.

## What We Know Right Now

- The public Connect API is enough to authenticate, run ad-hoc SQL, and create the smallest possible custom DMO.
- The unresolved gap is DLO to DMO mapping automation, not Salesforce session handling.
- Any future browser capture should focus on the mapping UI flow in Data Cloud rather than on already-proven public surfaces.
- The replay scaffold was verified in this repo with `doc:minimal-custom-dmo-public-surface` against a deliberately missing `/services/data/v64.0/ssot/mappings/nonexistent-replay-probe` path, which produced a recorded HTTP `404` artifact at `artifacts/probe_ui_replay-20260414T171435_691093Z.json`.

## Capture Workflow

1. Open Chrome DevTools on the Data Cloud page where the mapping action is triggered.
2. Filter the Network tab to `fetch` / `xhr`.
3. Trigger exactly one mapping action in the UI.
4. Copy the request path, method, request body, and the first response body that proves success or failure.
5. Sanitize org-specific identifiers before pasting the payload here.
6. Add a `replay-example` marker directly above the JSON payload so `probe_ui_replay.py` can load it.

## Template For A Captured Browser Endpoint

### Candidate: `<short-name>`

- Browser page: `Data Cloud -> Data Streams -> <stream> -> Mapping`
- Trigger action: `Click <button or deploy action>`
- Method + path: `POST /services/data/...`
- Auth requirements: `Authenticated Salesforce session from sf org display / browser cookie context`
- Extra headers observed: `List only if required beyond bearer auth and JSON`
- Observed prerequisite state: `Which DLO, DMO, or page state must exist first`

<!-- replay-example: replace-with-short-name -->
```json
{
  "replace": "with a sanitized browser-captured payload"
}
```

- Observed response:
```json
{
  "status": "replace with the first useful response payload"
}
```

- Replay command:
```bash
./.venv/bin/python d360-agentforce-lab/03-d360-config/scripts/probes/probe_ui_replay.py doc:replace-with-short-name /services/data/REPLACE_ME
```

## Seed Replay Fixture From A Proven Public Surface

This is not an internal browser endpoint. It is a doc-backed fixture derived from the accepted minimal custom DMO probe so the replay scaffold has a concrete example in the repo today.

### Candidate: `minimal-custom-dmo-public-surface`

- Browser page: `n/a - seeded from probe evidence rather than browser capture`
- Trigger action: `Replay the smallest known custom DMO create request`
- Method + path: `POST /services/data/v64.0/ssot/data-model-objects`
- Auth requirements: `Bearer token from sf org display`
- Extra headers observed: `Content-Type: application/json`
- Observed prerequisite state: `None; rename the DMO before a real replay if you want to avoid collisions`

<!-- replay-example: minimal-custom-dmo-public-surface -->
```json
{
  "category": "Profile",
  "fields": [
    {
      "dataType": "Text",
      "isPrimaryKey": true,
      "label": "Probe Key",
      "name": "probe_key"
    }
  ],
  "label": "Probe Minimal REPLACE_ME",
  "name": "Probe_Minimal_REPLACE_ME"
}
```

- Observed response:
```json
{
  "artifact": "artifacts/probe_create_custom_dmo-20260414T170126_843286Z.json",
  "result": "HTTP 201 Created on the live org when the name/label were unique"
}
```

- Replay command:
```bash
./.venv/bin/python d360-agentforce-lab/03-d360-config/scripts/probes/probe_ui_replay.py doc:minimal-custom-dmo-public-surface /services/data/v64.0/ssot/data-model-objects
```
