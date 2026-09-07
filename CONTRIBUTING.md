# Contributing

CompatForge accepts evidence only when its provenance and configuration grain are explicit.

## Development checks

```bash
python -m pip install -e ".[dev]"
ruff check pipeline tests
pytest -q
python -m compatforge_pipeline.validate data/fixtures

cd apps/web
npm install
npm run lint
npm run typecheck
npm run build
```

## Evidence contributions

Do not add real compatibility observations during Phase 1. The first reviewed external-source adapters and real evidence corpus are Phase 2/3 work.

When real evidence contribution opens, every record will require a source URL, source type, observed date, exact outcome, known configuration dimensions, and explicit limitations.
