# Evidence freshness automation

Phase 7A adds read-only automation around CompatForge's reviewed evidence corpus. It does not change the evidence trust model introduced in Phases 3 and 6.

## Goals

The scheduled review answers three questions:

1. Which reviewed observations and support statements are fresh, aging, or stale?
2. How is that evidence distributed by canonical device ID?
3. Are the upstream URLs referenced by the reviewed records still reachable?

The workflow produces review artifacts only. It never edits evidence, accepts a community report, records a publication receipt, or pushes a refresh commit.

## Freshness semantics

Phase 7A deliberately reuses the analytical data platform's existing thresholds:

- `fresh`: 0-180 days old;
- `aging`: 181-365 days old;
- `stale`: more than 365 days old.

Observations are aged from `observed_at`. Support statements are aged from `reviewed_at`. The `as_of` timestamp is explicit, and future-dated evidence fails the report rather than being silently coerced.

`python -m compatforge_pipeline.evidence_review report` emits:

- a canonical JSON freshness/coverage report;
- a SHA-256 over the deterministic report payload;
- per-device observation/support counts;
- per-device freshness counts and age bounds;
- explicit aging and stale review queues;
- a deduplicated inventory of referenced upstream URLs;
- an optional Markdown summary for the GitHub Actions job summary.

The report is deterministic for the same reviewed corpus and the same `as_of` timestamp.

## Upstream source checks

`python -m compatforge_pipeline.evidence_review check-sources` performs bounded, read-only HTTP checks for the URLs already present in the reviewed evidence. It records the response status, final URL, ETag and Last-Modified header when available.

A broken or redirected upstream URL is a review signal. It does not mutate an observation, support statement, claim state, source URL or publication record.

The source-check report is intentionally not treated as deterministic evidence: the network can change between runs. It is linked back to the exact deterministic freshness report SHA-256 so a reviewer can see which corpus produced the URL inventory.

## Scheduled workflow

`.github/workflows/refresh-evidence.yml` runs weekly and can also be started manually.

The workflow has only `contents: read` permission. It:

1. validates and loads the repository evidence through the existing CompatForge contract tooling;
2. builds the deterministic freshness and coverage report using that day's UTC boundary;
3. checks the referenced upstream sources;
4. writes the freshness summary to the GitHub Actions job summary;
5. uploads the JSON and Markdown review artifacts for 30 days.

There is no repository write permission and no Supabase credential in this workflow.

## Community evidence boundary

Phase 6C intentionally separates reviewer acceptance from public publication. Phase 7 automation must preserve that split.

An accepted community candidate is not public evidence until the exact candidate hash is committed to `data/evidence/observations/`, passes the normal evidence/data/web CI, is merged, and the admin publication receipt is recorded against the merged commit.

Phase 7A does not automate that operation. A later Phase 7C may prepare bounded pull requests from accepted candidates, but it must never bypass the candidate SHA-256, code review, CI, merge or publication-receipt gates.

## Next Phase 7 slices

- **Phase 7B:** permitted vendor adapters and source-content change reports. Adapters must be source-specific and must produce review candidates rather than auto-rewriting canonical evidence.
- **Phase 7C:** accepted-community-candidate refresh PRs and publication-batch assistance, preserving the Phase 6C hash/review/merge/admin gates.
- **Phase 7D:** broader coverage analytics and targeted stale-evidence work queues after the automation surfaces are proven stable.
