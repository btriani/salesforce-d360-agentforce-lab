# Phase 3 Programmatic Completion Design

## Problem

The Salesforce Data Cloud + Agentforce lab is blocked in Phase 3.

The desired outcome is a reproducible public repo that finishes the real Data Cloud flow:

- external Databricks data available in Data Cloud
- custom DMOs for external data
- a Calculated Insight for account-level Customer Health Score
- 3 Segments derived from that score
- an Agentforce agent grounded in those outputs

The current blocker is that Calculated Insights appear to require DMOs rather than DLOs, while the programmatic path for creating custom DMOs and mapping external DLOs into them is not yet working reliably in the current org.

## Goal

Finish the lab as a reproducible public repo with a programmatic-first Phase 3.

The repo should prefer stable and documented automation, but it may also use metadata deployment or reverse-engineered internal endpoints if those are the only viable way to complete the workflow. Unsupported surfaces must be labeled clearly in the docs.

## Non-Goals

- Guarantee that every Phase 3 step uses only public Salesforce APIs
- Preserve the current repo structure if a different layout better supports investigation and reproducibility
- Assume Developer Edition is the root cause without evidence

## Design Principles

1. Programmatic first. Every Phase 3 step should be attempted in code before being accepted as manual.
2. Evidence before conclusions. Every failure point should produce request, response, and scope notes.
3. Reproducibility over elegance. A brittle but documented path is preferable to an incomplete lab.
4. Honest platform boundaries. If a step requires unsupported endpoints or UI-only work, say so explicitly.
5. Practitioner value first. The repo should help Salesforce and Data Cloud practitioners finish the lab, not just study the failure.

## Recommended Approach

Use a layered investigation-and-completion ladder for Phase 3:

1. Try documented and public APIs for custom DMO creation, mapping, Calculated Insights, and Segments.
2. Try metadata deployment surfaces where applicable.
3. Inspect D360 UI network calls and reproduce working backend requests in code.
4. Use the smallest possible manual fallback only if programmatic approaches cannot complete the workflow.

This keeps the repo oriented toward automation while avoiding another dead-end built on guesses.

## Architecture

### Phase 3 Tracks

Phase 3 should be organized into three explicit tracks.

#### Track A: Environment and Data Readiness

This track proves the underlying lab data is correct before any custom DMO work starts.

- verify Salesforce auth and org access
- verify all 7 data streams exist
- verify expected fields are present on external streams
- verify CRM DMOs are populated
- verify external DLOs are queryable
- run the known-good cross-source Health Score SQL via ad-hoc query
- save or print evidence that the account-level result set is valid

#### Track B: Programmatic DMO and Mapping Investigation

This track attempts to solve the actual blocker in a structured way.

- probe custom DMO creation with smallest valid payloads
- expand field types incrementally to isolate payload or schema failures
- test naming rules, category values, data types, and required metadata
- search for a programmatic DLO -> DMO mapping surface
- test metadata deployment if relevant objects can be represented there
- inspect D360 UI requests and replay them if public surfaces are incomplete

Each experiment must capture:

- endpoint used
- request body
- response status
- response body
- observed side effect in the org
- conclusion

#### Track C: Programmatic Completion

Once Track B finds a viable surface, use it to complete the real workflow:

- create the 3 custom DMOs for Web Analytics, Product Usage, and Firmographic
- map the external DLO fields into those DMOs
- verify DMO population
- create the Customer Health Score Calculated Insight
- create the 3 Segments
- verify the outputs for Phase 4 Agentforce grounding

## Repository Restructure

The current Phase 3 area should be restructured around what is stable versus what is exploratory.

Proposed layout:

```text
d360-agentforce-lab/03-d360-config/
├── README.md
├── docs/
│   ├── decision-log.md
│   ├── public-api-notes.md
│   └── internal-endpoints.md
└── scripts/
    ├── probes/
    │   ├── probe_create_custom_dmo.py
    │   ├── probe_dmo_field_types.py
    │   ├── probe_mapping_surfaces.py
    │   └── probe_ui_replay.py
    ├── verify/
    │   ├── verify_readiness.py
    │   └── verify_phase3_outputs.py
    ├── workflows/
    │   ├── create_custom_dmos.py
    │   ├── map_external_dlos.py
    │   ├── create_health_score_ci.py
    │   └── create_segments.py
    └── _common.py
```

Purpose of this split:

- `probes/` contains experiments and evidence-gathering tools
- `workflows/` contains the best known reproducible path
- `verify/` contains assertions used before and after setup
- `docs/` records what actually works in the org

## Documentation Strategy

### README Positioning

The Phase 3 README should present the workflow in this order:

1. readiness verification
2. recommended programmatic path
3. unsupported/internal path if needed
4. minimal manual fallback if still required
5. final verification

The root README should describe the repo as:

"A reproducible D360 + Agentforce lab with programmatic setup wherever the platform allows it, plus clearly documented fallback paths where Data Cloud configuration surfaces are incomplete or unstable."

### Decision Log

The Phase 3 docs should include a short decision log explaining:

- which API surfaces were tested
- which ones failed
- which one actually worked
- whether the result depends on unsupported endpoints
- what a learner should try first

This turns the blocker into reusable practitioner knowledge instead of a hidden repo quirk.

## Technical Boundaries

The spec should not claim that Developer Edition is the cause unless verified.

The only defensible statement right now is:

- ad-hoc cross-source query capability works
- Calculated Insight creation works for CRM DMOs
- the unresolved gap is external custom DMO lifecycle and or DLO -> DMO mapping automation in the current org and API surface

Possible causes to investigate:

- incorrect request body shape
- unsupported field combinations or data types
- undocumented prerequisites for realistic DMOs
- missing mapping API knowledge
- org or edition-specific limits

## Success Criteria

The Phase 3 work is complete when the repo can do the following in a repeatable way:

1. verify readiness and prove the Health Score logic with ad-hoc cross-source SQL
2. create or provision the needed custom DMOs
3. populate those DMOs from the 3 external DLOs
4. create the account-level Customer Health Score Calculated Insight
5. create At Risk, Healthy, and Upsell Ready Segments
6. verify those outputs for use in Phase 4

If programmatic completion is not fully possible, the repo must still:

- identify the exact failing boundary
- preserve all evidence
- provide the smallest possible fallback to finish the lab

## Risks

- reverse-engineered endpoints may change without notice
- metadata support may be partial or absent for Data Cloud artifacts
- propagation delays may make automation look flaky when the requests are actually correct
- the current org may not expose every capability needed for a pure API path

## Recommendation

Proceed with a programmatic-first implementation that treats Phase 3 as both:

- a real completion effort for the lab
- a structured investigation into which D360 surfaces are actually automatable

The repo should be reorganized to make those two goals explicit and to keep the final public experience credible even if some steps depend on unsupported internals or a last-resort manual fallback.
