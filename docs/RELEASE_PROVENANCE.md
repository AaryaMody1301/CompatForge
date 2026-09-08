# Release provenance and immutable manifests

Phase 8C creates one verifiable release-provenance chain across CompatForge's reviewed data, web build and existing hardware CLI release surface.

## Trust model

A CompatForge release is identified by a full 40-character Git commit SHA. The top-level release manifest records that SHA and hashes the repository inputs that define the released identity, evidence, web and transformation state.

The release workflow never downloads a mutable upstream identity feed to decide what belongs in a tagged release. Upstream refreshes remain review candidates. A release therefore describes the reviewed repository state at the tagged commit, not whatever an upstream server happens to return during a later workflow rerun.

The manifest groups reviewed inputs as follows:

- `identity`: the reviewed `usb.ids` source policy plus the public device catalog;
- `evidence`: canonical observations, vendor support statements, vendor semantic baselines and the packaged offline resolver snapshot;
- `web`: the web package/lock/config plus application source;
- `transformations`: dbt models plus the deterministic identity/evidence pipeline implementations.

Every file entry includes its repository-relative path, byte size and SHA-256. Each group also has a canonical group SHA-256. The complete manifest has its own canonical `manifest_sha256`.

## Web release artifact

`tools/package_web_release.py` packages the successful Next.js production build into `compatforge-web-build.tar.gz`.

Archive metadata is normalized:

- gzip timestamp is zero;
- tar entry timestamps are zero;
- uid/gid and owner/group names are normalized;
- file modes are fixed;
- entries are sorted;
- `.next/cache` and `.next/diagnostics` are excluded.

This makes the archive byte-stable when the selected build files are byte-identical while avoiding transient build caches.

The release workflow also produces `compatforge-web.spdx.json` from the built web workspace.

## Release files

The verified Phase 8C bundle contains:

```text
compatforge-web-build.tar.gz
compatforge-web.spdx.json
COMPATFORGE_RELEASE_MANIFEST.json
SHA256SUMS.txt
```

`COMPATFORGE_RELEASE_MANIFEST.json` binds the web artifacts to the reviewed repository inputs and exact source commit. `SHA256SUMS.txt` is a conventional checksum index for the distributed artifacts plus the top-level manifest.

## Build and verify locally

Build the web application first:

```bash
cd apps/web
npm ci
npm run build
cd ../..
```

Package the web output:

```bash
python tools/package_web_release.py \
  --web-root apps/web \
  --output build/release/compatforge-web-build.tar.gz
```

Place the generated web SPDX file at `build/release/compatforge-web.spdx.json`, then create the manifest using the exact commit being released:

```bash
python -m compatforge_pipeline.release_manifest build \
  --repository-root . \
  --release-root build/release \
  --commit "$(git rev-parse HEAD)" \
  --release-name "compatforge-$(git rev-parse HEAD)" \
  --artifact compatforge-web-build.tar.gz \
  --artifact compatforge-web.spdx.json
```

Verify every reviewed source digest, every release-artifact digest, the manifest self-hash and the expected commit:

```bash
python -m compatforge_pipeline.release_manifest verify \
  --repository-root . \
  --release-root build/release \
  --manifest build/release/COMPATFORGE_RELEASE_MANIFEST.json \
  --expected-commit "$(git rev-parse HEAD)"
```

Any edited canonical evidence record, catalog/source input, transformation input, web source, lockfile, web build or SBOM fails verification.

## GitHub Actions boundary

`.github/workflows/release-provenance.yml` has two jobs.

`build-release-bundle` runs with `contents: read` only. On pull requests it:

1. verifies the packaged offline evidence snapshot still matches canonical evidence;
2. installs the committed web lockfile;
3. builds the Next.js production output;
4. packages the web build;
5. generates the SPDX SBOM;
6. builds and immediately re-verifies the release manifest;
7. uploads the verified bundle as a workflow artifact.

`attest-release-bundle` does not run for pull requests. It runs only for manual or `v*` tag events and receives the additional `id-token: write` and `attestations: write` permissions required for GitHub artifact attestations.

The attestation job signs:

- `COMPATFORGE_RELEASE_MANIFEST.json` with build provenance;
- `compatforge-web-build.tar.gz` with build provenance plus its SPDX SBOM predicate.

It then verifies both subjects with `gh attestation verify` before the workflow is considered successful.

The existing hardware CLI workflow continues to attest each native archive and its SPDX SBOM. Phase 8C broadens provenance to the top-level release/data/web surface rather than replacing the CLI-specific attestations.

## What an attestation proves

An attestation proves that a named artifact digest was produced by an identified GitHub Actions workflow from a particular repository/ref/commit context. It does not prove that the code is vulnerability-free or that the compatibility evidence is universally correct. Those remain separate review, security, evidence-quality and release-acceptance gates.

## Phase 8D handoff

Phase 8D uses these outputs to perform the final release-candidate and `v1.0.0` acceptance process. It must still verify hosted OAuth/moderation configuration, repository branch/ruleset immutability, release rollback instructions and all required CI/security gates before publishing `v1.0.0`.
