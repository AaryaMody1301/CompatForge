# Public web product

CompatForge's public web application is read-only by default. Community submissions are an explicit hosted feature that is exposed only when authentication and moderation are configured and enabled.

## Routes

```text
/                       product overview and corpus counts
/check                  configuration-level compatibility checker
/devices                searchable published USB identity catalog
/devices/[slug]         identity details, support statements, observations, sources, timeline
/coverage               evidence-presence coverage by device
/methodology            resolver and evidence rules
/submissions            optional community contribution surface
```

## Data path

The web app imports reviewed JSON records under `data/evidence/` directly into server-side TypeScript modules. The repository remains the source of truth; the web app does not duplicate the public evidence body in a second store.

The product consumes the complete versioned USB ID Repository snapshot from `data/catalog/usb-device-catalog.json`. The smaller `data/catalog/curated-devices.json` file is a CompatForge-owned metadata overlay for stable slugs, aliases, categories, and summaries. Catalog identity never implies compatibility.

Catalog search is server-rendered, token-ranked, and paginated. Evidence-backed and curated developer hardware is presented before the raw registry on the default browse page. Generic identity pages are rendered on demand, while curated device pages are pre-rendered. Checker and submission forms use canonical VID/PID fields linked to the searchable catalog instead of rendering tens of thousands of HTML options.

## Rendering model

- Shared product and device pages are Server Components.
- Search and checker pages use URL query parameters and native HTML GET forms.
- No client state, client data-fetching library, analytics SDK, or component framework is required.
- External evidence links point to the original reviewed sources.
- Raw identity-only pages remain accessible but are not indexed as standalone search-engine landing pages.

## Compatibility checker

The checker mirrors the deterministic resolver semantics used by the Python tooling:

1. Keep observed compatibility and vendor support as separate answers.
2. For observations, prefer exact host + OS + architecture + connection matches.
3. If needed, relax host identity and then OS version; label the relaxation.
4. Never relax architecture, OS family, or connection path.
5. Preserve conflicting evidence.
6. Return `unknown` when no applicable evidence exists.

A related observation can be shown without being promoted into a result. For example, an FT232R report with an `unspecified` USB topology cannot prove direct-port or hub compatibility.

## Deployment

The production web project uses `apps/web` as its Vercel project root and follows the merged `main` branch. Pull requests are validated by the repository's Next.js build and browser-acceptance gate; production deployment is not part of repository cleanup or local validation.

Community features are opt-in through `COMPATFORGE_COMMUNITY_ENABLED=1` plus the documented Supabase configuration. See `docs/AUTH_SETUP.md`.
