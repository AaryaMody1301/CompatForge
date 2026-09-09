# Contributing

CompatForge accepts changes only when identity, evidence, and release provenance remain explicit.

## Development checks

```bash
python -m pip install -e ".[dev,data]"
ruff check pipeline tests
pytest -q
python -m compatforge_pipeline.validate \
  data/fixtures \
  data/evidence/vendor \
  data/evidence/observations
compatforge-snapshot verify \
  --observations data/evidence/observations \
  --support data/evidence/vendor

cd apps/web
npm ci
npm run lint
npm run typecheck
npm run build
```

Pull requests also run browser acceptance, deterministic data builds, dependency audits, CodeQL, database/RLS tests, release-provenance verification, and six-platform frozen CLI builds.

## Device identities

A device may be added to the reviewed catalog when its canonical USB VID/PID and product identity are supported by a public source. Identity data must not imply compatibility. If the repository has no reviewed support statement or observation for that device, the product must continue to report compatibility as unknown.

## Compatibility evidence

Compatibility observations and vendor-support statements belong under `data/evidence/` and must satisfy the public schemas. Every real record requires explicit provenance, date, configuration scope, outcome/support state, and limitations where applicable.

Do not turn vendor documentation into an observed success, broaden a configuration silently, or remove conflicting evidence to create a cleaner answer.

Community submissions follow the authenticated moderation and publication workflow documented in [`docs/MODERATION.md`](docs/MODERATION.md). Database acceptance is not public evidence until the accepted candidate is merged into the reviewed repository snapshot and its publication receipt is recorded.

## Release-sensitive changes

Changes to catalog data, reviewed evidence, release tooling, workflows, package locks, or web source are covered by release provenance. Keep third-party actions pinned according to the workflow security policy and do not bypass failing release/security gates.
