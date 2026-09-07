# CompatForge

Evidence-first hardware compatibility intelligence.

CompatForge is being built to answer a narrow but difficult question:

> Will this peripheral work with this host, operating system, architecture, driver, firmware, and connection path - and what evidence supports that answer?

The project treats compatibility as a configuration-level evidence problem rather than a binary device-to-laptop lookup. Missing evidence stays `UNKNOWN`; conflicting evidence stays visible; source observations are never rewritten into stronger claims than they support.

## Phase 1 status

Phase 1 establishes the contracts that later product features depend on:

- canonical USB device identity rules;
- machine-readable device and compatibility-observation schemas;
- evidence-source and outcome semantics;
- synthetic fixtures and contract regression tests;
- repository privacy/provenance boundaries;
- an initial Next.js App Router shell;
- CI for Python contracts and the web build.

No real-world compatibility result is published by this phase.

## Initial scope

The first public data release will focus on developer and engineering USB peripherals:

- USB serial adapters;
- development boards;
- debuggers/programmers;
- logic analyzers.

Initial operating-system scope is Windows 11, macOS, and Ubuntu on `x86_64` and `arm64`. Direct USB and hub-mediated connections are modeled explicitly.

## Repository layout

```text
apps/web/                  Next.js product shell
pipeline/compatforge_pipeline/
                           validation and identity tooling
schemas/                   public JSON Schema contracts
data/fixtures/             synthetic reviewed examples
tests/                     contract and identity regression tests
docs/                      architecture, data, evidence, privacy, roadmap
.github/workflows/ci.yml   repository verification
```

## Validate the data contracts

Python 3.13+:

```bash
python -m pip install -e ".[dev]"
python -m compatforge_pipeline.validate data/fixtures
pytest -q
ruff check pipeline tests
```

## Run the web shell

Next.js 16 requires Node.js 20.9 or newer. From `apps/web`:

```bash
npm install
npm run dev
```

The Phase 1 CI workflow also runs lint, TypeScript checking, and a production build. A committed npm lockfile is a Phase 1 merge gate; the initial CI run is allowed to generate it so the reviewed dependency graph can be committed before merge.

## Evidence rule

A compatibility observation must identify, at minimum:

- what device was involved;
- the host and CPU architecture;
- the operating system and version;
- the connection path;
- the observed outcome;
- the evidence source and source type;
- when the result was observed and recorded.

See [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md).

## Project principles

1. Unknown is a valid result.
2. Evidence and derived claims are separate records.
3. Compatibility specificity must never be silently broadened.
4. Conflicting evidence is preserved, not averaged away.
5. Raw source provenance and licensing are release requirements.
6. Diagnostic collection must be inspectable and privacy-minimized.

## License

Project source code is MIT licensed. Third-party source data keeps its upstream license and attribution requirements; it will be tracked separately in `THIRD_PARTY_NOTICES.md` and source manifests.
