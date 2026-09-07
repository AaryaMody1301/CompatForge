# Public web MVP

Phase 4 turns the reviewed CompatForge evidence corpus into a read-only product without adding a live database, account system, or paid API.

## Routes

```text
/                       product overview and corpus counts
/check                  configuration-level compatibility checker
/devices                searchable reviewed catalog
/devices/[slug]         support statements, observations, sources, timeline
/coverage               evidence-presence coverage by device
/methodology            resolver and evidence rules
```

## Data path

The web app imports the reviewed JSON records under `data/evidence/` directly into server-side TypeScript modules. The repository remains the source of truth; the web app does not duplicate the evidence body in a second store.

The initial catalog has a small explicit device metadata list for the reviewed devices. This is intentionally simpler than introducing a second identity service before catalog scale requires one.

## Rendering model

- Shared product and device pages are Server Components and can be prerendered.
- Search and checker pages use URL query parameters and native HTML GET forms.
- No client state, client data-fetching library, analytics SDK, or component framework is required.
- External evidence links point to the original reviewed sources.

## Compatibility checker

The checker mirrors the Phase 3 resolver semantics needed by the web product:

1. Keep observed compatibility and vendor support as separate answers.
2. For observations, prefer exact host + OS + architecture + connection matches.
3. If needed, relax host identity and then OS version; label the relaxation.
4. Never relax architecture, OS family, or connection path.
5. Preserve conflicting evidence.
6. Return `unknown` when no applicable evidence exists.

A related observation can be shown without being promoted into a result. For example, an FT232R report with an `unspecified` USB topology cannot prove direct-port or hub compatibility.

## Deployment

The intended first deployment is Vercel with `apps/web` as the project root. All application dependencies are already locked in `apps/web/package-lock.json`, and evidence JSON is bundled through static imports from the repository.

Preview deployments should be verified before Phase 4 is merged. Production deployment follows the `main` branch after the preview is accepted.
