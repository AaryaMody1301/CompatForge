# Standalone hardware CLI release

Phase 5C turns the local diagnostic workflow into a downloadable `compatforge-hw` executable. The executable contains the reviewed local compatibility snapshot and public JSON Schemas, so diagnostics and explanations do not require Python, a source checkout, a database, or network access.

## Supported release targets

Each release candidate builds natively on its target architecture:

| Platform | Architecture | Asset |
| --- | --- | --- |
| Linux | x86_64 | `compatforge-hw-linux-x86_64.tar.gz` |
| Linux | arm64 | `compatforge-hw-linux-arm64.tar.gz` |
| Windows | x86_64 | `compatforge-hw-windows-x86_64.zip` |
| Windows | arm64 | `compatforge-hw-windows-arm64.zip` |
| macOS | Intel x86_64 | `compatforge-hw-macos-x86_64.tar.gz` |
| macOS | Apple silicon arm64 | `compatforge-hw-macos-arm64.tar.gz` |

The release workflow uses native GitHub-hosted runners for every target. PyInstaller is not used as a cross-compiler.

## Commands

```bash
compatforge-hw --version
compatforge-hw snapshot-info
compatforge-hw diagnose --host-only --output diagnostic.json
compatforge-hw diagnose --device usb:0403:6001 --output diagnostic.json
compatforge-hw explain --diagnostic diagnostic.json --output explanation.json
```

The older development console scripts remain available from the Python package, but the standalone release surface is the single `compatforge-hw` command.

## Explicit contribution handoff

Phase 5C still does not submit data. A user can prepare a local handoff only after explicitly approving the export:

```bash
compatforge-hw prepare-contribution \
  --diagnostic diagnostic.json \
  --explanation explanation.json \
  --approve-export \
  --output contribution-handoff.json
```

Without `--approve-export`, the command fails and writes no handoff. The handoff contains an explicit `evidence_ready: false` marker. It is configuration context for a future Phase 6 submission flow, not a compatibility observation and not public evidence.

The command performs no network request and no upload. The user can inspect or delete the JSON locally.

## Release integrity

Each release candidate contains:

- one platform archive;
- an SPDX JSON SBOM for every platform archive;
- `SHA256SUMS.txt`;
- `RELEASE_MANIFEST.json` with tag, commit, size, and SHA-256 for every asset;
- GitHub build-provenance attestations for platform archives;
- GitHub SBOM attestations for platform archives.

Verify a downloaded archive with GitHub CLI:

```bash
gh attestation verify compatforge-hw-linux-x86_64.tar.gz \
  --repo AaryaMody1301/CompatForge
```

For an SPDX SBOM attestation:

```bash
gh attestation verify compatforge-hw-linux-x86_64.tar.gz \
  --repo AaryaMody1301/CompatForge \
  --predicate-type https://spdx.dev/Document/v2.3
```

Also compare the archive SHA-256 with `SHA256SUMS.txt` or `RELEASE_MANIFEST.json` before running it.

## Signing boundary

GitHub artifact attestations prove repository/workflow/commit provenance. They are not Apple notarization and are not Windows Authenticode signatures. Phase 5C does not claim OS-vendor code signing without the required certificates and platform signing services.

Do not bypass operating-system security controls to run an untrusted binary. If a device or organization policy requires notarized or Authenticode-signed software, install the reviewed Python source/package in an isolated environment until native signing is introduced.

## First public tag gate

There are currently no CompatForge GitHub Releases. Before creating the first `hw-cli-v*` tag, enable GitHub immutable releases in repository settings. Then create a release tag only after the release workflow is green on the exact commit.

Recommended first release-candidate tag:

```text
hw-cli-v0.3.0rc1
```

The tag workflow builds all targets again, creates provenance/SBOM attestations, aggregates checksums and the manifest, and publishes the GitHub Release. Release publication is never triggered by a pull request.

## Naming boundary

The standalone executable is `compatforge-hw` and the Python distribution remains `compatforge-hw-pipeline`. Do not publish this project under the Python package name `compatforge`, which is already used by an unrelated project.
