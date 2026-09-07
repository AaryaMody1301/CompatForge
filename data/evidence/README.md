# Reviewed compatibility evidence

This directory contains human-reviewed evidence records that are safe to validate and ingest into the CompatForge evidence platform.

## Layout

```text
vendor/        scoped support statements from official/vendor sources
observations/  reported or reproduced configuration-level outcomes
```

Support statements and observations are intentionally different record types. A vendor saying a platform is supported does not create an observed `works` result.

## Observation quality rule

Never fill an unknown configuration field by assumption. Phase 3B permits `connection_path.kind = unspecified` when a credible reproduction does not state whether the device used a direct port, hub, dock, or adapter. Those observations contribute to provenance and coverage but cannot satisfy a resolver query for a specific connection path.

## Review requirements

A real evidence record must:

- pass its JSON Schema;
- link to the original HTTPS source;
- use project-authored paraphrases rather than copied passages;
- state limitations explicitly;
- record observation/review and ingestion timestamps separately;
- avoid turning support documentation into reproduced compatibility.

Synthetic records belong under `tests/fixtures/evidence/` and are never published as real evidence.
