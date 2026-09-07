# Compatibility resolver

Phase 3 introduces a deterministic resolver with two deliberately separate outputs.

## Observed claim

`claim_state` is derived only from compatibility observations:

- `works`
- `works_with_conditions`
- `fails`
- `conflicting`
- `unknown`

Vendor documentation cannot by itself turn `unknown` into `works`.

## Vendor/support state

`support.state` is derived from scoped support statements:

- `supported`
- `supported_with_conditions`
- `unsupported`
- `conflicting`
- `unknown`

This keeps two different questions separate:

1. What has actually been observed for this configuration or a controlled relaxation of it?
2. What does the vendor or support source document as supported?

## Observation specificity

The resolver checks observation evidence in this order:

1. `exact` - device, host model, architecture, OS family/version, and connection path match.
2. `host_relaxed` - host manufacturer/model may differ; architecture, OS family/version, and connection path must still match.
3. `os_version_relaxed` - host and OS version may differ; architecture, OS family, and connection path must still match.
4. `none` - no observation was found.

The resolver never relaxes CPU architecture, OS family, or connection path in Phase 3A. A relaxed result always sets `is_relaxed: true` and returns the exact evidence IDs used.

## Conflict rule

At the best available specificity tier, a mixture of successful (`works` or `works_with_conditions`) and failing observations produces `conflicting`. Evidence is never averaged into a numeric trust score.

## Support-statement matching

Support statements are matched by device ID, architecture, OS family/version rule, and connection scope. The most specific matching statements win. Support facts remain separate from observations even when they are from official vendor documentation.

## CLI example

```bash
python -m compatforge_pipeline.resolver \
  --query tests/queries/saleae-win11-x64.json \
  --observations data/fixtures \
  --support data/evidence/vendor
```

With the current reviewed corpus this query should return an observed claim of `unknown` and a vendor-support state of `supported_with_conditions`. That is intentional: CompatForge has documentation support but no exact reproduced host observation yet.
