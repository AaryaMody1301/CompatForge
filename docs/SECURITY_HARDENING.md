# Security hardening

Phase 8B adds enforceable repository and deployed-web security gates without introducing a privileged application credential or weakening the evidence/publication trust boundary.

## Pull-request supply-chain gate

`.github/workflows/security.yml` runs the GitHub native dependency-review action on pull requests targeting `main` as an additional dependency-diff signal.

GitHub currently documents the dependency graph as permanently enabled for public repositories, and dependency review is available when that graph is available. CompatForge is public, but repeated exact-head runs of `actions/dependency-review-action@v5` returned the action's generic `Dependency review is not supported on this repository` error. The action project also documents an open failure mode where API/rate-limit errors can be surfaced through the same misleading message.

Because the native action cannot currently provide a reliable blocking signal for this repository, Phase 8B does not make that platform error a release blocker. The native step is allowed to report a warning, while repository-owned current-state audits remain hard failures for every dependency ecosystem currently used by CompatForge:

- `npm audit --audit-level=high` against the committed `apps/web/package-lock.json` dependency graph;
- a Python audit over an exact `pip list --local --format=freeze --exclude-editable` snapshot after installing the full development/data/release dependency surface, then `pip-audit==2.10.1 --strict --no-deps` against those pinned third-party versions.

These current-state audits are stricter than a pull-request-only diff for vulnerability enforcement: a high-severity advisory fails even if the vulnerable dependency was merged before the advisory was published. The native dependency-review signal remains useful when GitHub's dependency-review API responds normally, but it is not trusted as the sole high-severity vulnerability gate.

The explicit installed-package snapshot excludes CompatForge's own editable source package while retaining strict collection behavior for every third-party distribution actually present in the CI environment.

The first successful strict Python dependency collection exposed `PYSEC-2026-1845` in `pytest 8.4.2`. CompatForge did not add a dev-only exception: the development dependency floor is now `pytest>=9.0.3,<10`, the fixed major line identified by the advisory, and the full Python contract suite plus strict dependency audit pass with the remediated dependency.

Dependabot is configured weekly for GitHub Actions, npm and Python dependency updates.

## Code scanning

CodeQL runs `security-extended` queries for both repository language families:

- `javascript-typescript`;
- `python`.

Both are interpreted-language analyses and use `build-mode: none`, so the security job does not need to execute repository build scripts to extract the code database.

The CodeQL job has only `contents: read` plus `security-events: write`, scoped to that job. Other security jobs retain the workflow-level `contents: read` permission.

## Workflow policy

`python -m compatforge_pipeline.workflow_security .github/workflows` rejects:

1. workflows without explicit top-level `permissions`;
2. `pull_request_target` triggers;
3. network-fetched shell scripts piped directly from `curl`/`wget` into a shell;
4. external action references without a version;
5. mutable third-party action references.

GitHub-maintained `actions/*` and `github/*` actions may track a major tag such as `@v6` or `@v4`. Other action owners must use a full 40-character commit SHA. Existing release-critical third-party actions are already SHA-pinned.

The policy intentionally does not pretend that a YAML text check replaces repository settings, review, CodeQL, dependency auditing, or secret scanning.

## Secret scanning boundary

CompatForge is public, so GitHub secret scanning is a platform-provided control. Phase 8B does not create a workflow that reads repository secrets or exports secret-scanning alert content into CI logs.

Repository push-protection and release/ruleset settings are administrative controls and are verified during Phase 8D rather than changed implicitly from a code pull request.

## Web response headers

`apps/web/next.config.ts` applies the following headers to every route:

| Header | Required value / purpose |
| --- | --- |
| `Content-Security-Policy` | `base-uri 'self'; frame-ancestors 'none'; object-src 'none'` |
| `Permissions-Policy` | disables camera, microphone, geolocation and browsing-topics |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | two-year HTTPS-only policy with subdomains/preload |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` legacy clickjacking defense |

`poweredByHeader: false` remains enabled, and browser acceptance now fails if `X-Powered-By` is exposed.

The CSP is intentionally non-breaking and narrow in Phase 8B. It protects base URL injection, plugin/object embedding, and framing without adding brittle static `script-src` rules around Next.js inline runtime data or future Supabase OAuth navigation. A nonce/hash-based script policy can be added later only with a dedicated runtime design and browser acceptance coverage.

## Acceptance

The Phase 8A browser suite now validates all six required security headers on every reviewed route, including the custom 404 response. The same script is used by:

- pull-request CI against the exact local `next build`/`next start` output;
- the scheduled/manual production smoke against the stable Vercel alias.

A missing/mutated header, exposed `X-Powered-By`, wrong HTTP status, missing reviewed DOM marker, or runtime error marker fails the gate.

## Remaining repository-setting gates

Phase 8B no longer treats the native dependency-review API error as a repository-setting blocker because GitHub's current public-repository documentation states that the dependency graph is permanently enabled for public repositories and repeated native-action runs still return the generic unsupported error. The Python and npm dependency audits remain blocking.

At the start of Phase 8B, `main` is not branch-protected and the repository has no rulesets. Those release-immutability controls remain Phase 8D work rather than being changed implicitly from this code pull request.
