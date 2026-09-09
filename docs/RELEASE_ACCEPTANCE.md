# Release acceptance and rollback

Phase 8D is the final operational gate before CompatForge `v1.0.0`. It does not treat a green unit-test suite as sufficient release evidence. A release candidate must bind the reviewed repository state, the deployed production commit, repository protections, immutable GitHub releases, attestations, and the existing hosted acceptance gates.

## Initial Phase 8D audit

At the start of Phase 8D:

- `main` points at the merged Phase 8C commit `f6cf2b1c34dbe8367312da3e5e90a25230be3c40`;
- the Vercel production deployment for that exact commit is `READY`;
- no production runtime errors were reported by Vercel for the preceding seven-day window;
- `main` is not protected;
- the repository has no active rulesets;
- there are no GitHub Releases yet.

The last three items are release blockers. Phase 8D intentionally makes them fail the live preflight instead of documenting them as warnings.

## 1. Repository settings required before any release tag

### Enable immutable releases

In the repository settings, enable **Release immutability** under the Releases section. This must be enabled before the first release is published; enabling it later does not retroactively make an existing release immutable.

Create a fine-grained GitHub token with access only to this repository and **Administration: read** permission. Store it as the Actions secret:

```text
COMPATFORGE_RELEASE_ADMIN_TOKEN
```

The token is used only to read `GET /repos/AaryaMody1301/CompatForge/immutable-releases`. Release publication itself continues to use the job-scoped `GITHUB_TOKEN`.

### Protect `main`

Create an active branch ruleset for the default branch. At minimum:

- require changes through pull requests;
- require the existing CI/security/database/release checks before merge;
- block force pushes;
- block branch deletion.

After configuration, `GET /repos/AaryaMody1301/CompatForge/branches/main` must report `protected: true` and the repository rulesets endpoint must contain at least one active ruleset.

### Protect release tags

Create an active tag ruleset covering both release families:

```text
refs/tags/v*
refs/tags/hw-cli-v*
```

Prevent release-tag updates and deletion. Restrict tag creation to the intended release actor/bypass path. Published immutable releases additionally lock their associated tag and release assets, but the tag ruleset protects the interval before publication.

## 2. Production commit provenance

`apps/web/next.config.ts` emits this public response header:

```text
X-CompatForge-Commit: <40-character Git commit SHA>
```

On Vercel it is sourced from `VERCEL_GIT_COMMIT_SHA`. Local builds fall back to `COMPATFORGE_BUILD_COMMIT` and then `local`.

The live release preflight rejects a release when the canonical production URL does not report the exact commit being released. This prevents tagging a commit before the corresponding production deployment is actually ready.

## 3. Live release preflight

Run **Actions -> CompatForge Release Acceptance -> Run workflow** from `main` and supply a tag candidate such as:

```text
v1.0.0-rc.1
```

The workflow fails unless all of these conditions are simultaneously true:

1. the dispatch commit is the current `main` commit;
2. `main` is protected;
3. at least one active repository ruleset exists;
4. the requested release tag has not already been used by a GitHub Release;
5. GitHub reports immutable releases enabled through the administration-read API;
6. `https://compat-forge.vercel.app/` returns `X-CompatForge-Commit` equal to the exact `main` SHA.

The resulting JSON and Markdown acceptance report is retained as a workflow artifact.

Do not create a release tag until this preflight is green.

## 4. Hardware CLI release candidate

After the live preflight and hosted product checks are green, create the first CLI candidate at the same protected `main` commit:

```text
hw-cli-v0.3.0rc1
```

The hardware CLI workflow rebuilds and smoke-tests all six platform/architecture binaries, generates SPDX SBOMs and attestations, and then rechecks the protected-main/ruleset/immutable-release gates before publication.

Publication follows the immutable-release-safe sequence:

1. assemble every asset plus `SHA256SUMS.txt` and `RELEASE_MANIFEST.json`;
2. create a **draft** GitHub Release and attach all assets;
3. publish the draft only after all assets are present;
4. run `gh release verify`;
5. run `gh release verify-asset` for every attached asset.

A rerun cannot silently replace a published immutable release.

## 5. Top-level `v1.0.0` release candidate

For the overall product candidate, create:

```text
v1.0.0-rc.1
```

The release-provenance workflow:

1. rebuilds the deterministic web release artifact;
2. generates the web SPDX SBOM;
3. builds and verifies the exact-commit release manifest and checksums;
4. generates and immediately verifies GitHub attestations;
5. reruns the live release preflight against the tag commit;
6. creates a draft release with every verified asset;
7. publishes the draft;
8. verifies that the resulting release is immutable and every local asset matches the published release asset.

If Vercel has not yet promoted the tagged commit to production, publication stops before a GitHub Release is created. Rerun the failed job only after production reports the same commit SHA.

## 6. Hosted acceptance that still requires configured accounts

Before final `v1.0.0`, complete the existing hosted acceptance procedures rather than replacing them with synthetic CI:

- GitHub OAuth through the configured Supabase provider;
- signed-in submission creation and user-scoped queue visibility;
- cross-account RLS isolation;
- database-enforced rate limiting and opaque duplicate signaling;
- moderator queue/review using an allowlisted moderator membership;
- one accepted candidate -> reviewed repository PR -> CI -> merge -> publication-receipt cycle;
- Phase 7C refresh automation with the configured least-privilege Supabase identity and GitHub refresh token.

Use `docs/AUTH_SETUP.md`, `docs/MODERATION.md`, and `docs/COMMUNITY_REFRESH_AUTOMATION.md` for those exact procedures. Do not put a Supabase service-role key in the web application to make acceptance easier.

## 7. Final `v1.0.0`

Publish `v1.0.0` only when:

- `v1.0.0-rc.1` (or a later RC) passed all repository, deployment, security, provenance, and hosted acceptance gates;
- no release-blocking changes have been merged since that accepted RC without repeating acceptance;
- the live release preflight passes for the exact final commit;
- all normal PR checks are green on that commit.

Then tag the accepted protected `main` commit as `v1.0.0`. The same release-provenance workflow publishes and verifies the immutable final release.

## Rollback policy

### Before publication

If a draft or build is wrong, stop the workflow before publishing. Fix the source through a normal pull request and run acceptance again. Do not weaken a failed gate to salvage the candidate.

### After an immutable release is published

Never replace, move, or mutate a released tag or asset. GitHub immutable releases intentionally prevent those operations.

For a CLI defect, fix the source and publish a new candidate or patch release. For a production web regression, Vercel may be rolled back to the previous known-good deployment while the fix goes through the normal PR/release process. The GitHub release remains an immutable record of what was actually released.

If a final `v1.0.0` defect requires a source fix, publish a new semantic-versioned release (for example `v1.0.1`) after repeating the release gates. Do not delete `v1.0.0` with the intention of reusing the tag name.
