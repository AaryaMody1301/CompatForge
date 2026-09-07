# Local diagnostic agent

Phase 5 provides an inspectable, local-only diagnostic workflow. The agent does not upload data and does not attempt to fix, enable, disable, flash, or reconfigure hardware.

## Phase 5C standalone command

The downloadable release exposes one end-user command:

```bash
compatforge-hw --version
compatforge-hw snapshot-info
compatforge-hw diagnose --host-only --output diagnostic.json
compatforge-hw diagnose --device usb:0403:6001 --output diagnostic.json
compatforge-hw explain --diagnostic diagnostic.json --output explanation.json
```

The Python distribution retains the older development console scripts (`compatforge-diagnose`, `compatforge-explain`, and `compatforge-snapshot`) for repository workflows. The standalone binary uses the unified `compatforge-hw` surface.

The diagnostic manifest and local compatibility explanation are deliberately separate JSON records. Collection records local facts; the explanation is a derived claim from the packaged reviewed snapshot.

## Privacy model

The diagnostic contract is allowlist-based. A target-device manifest can contain:

- OS family/name/version/build;
- CPU architecture;
- host manufacturer/model;
- the requested USB VID/PID identity;
- whether that target was observed;
- a safe target count;
- connection class when it can be inferred safely;
- USB link speed when available;
- target-scoped driver name/provider/version when a privacy-reviewed collector exposes it.

It does not contain serial numbers, usernames, hostnames, MAC addresses, IP addresses, Wi-Fi identifiers, filesystem paths, raw device instance IDs, or unrelated USB inventory. There is no automatic upload path.

The command requires either one canonical device ID or `--host-only`; there is deliberately no "dump every connected USB device" mode.

## Driver metadata

### Windows

Target presence comes from `Get-PnpDevice -PresentOnly`. Filtering by VID/PID happens inside PowerShell before JSON is returned to Python. For matching instances only, the collector reads driver description, provider, and version. The raw PnP instance ID is used locally for the property lookup but is never returned to Python or written into the manifest.

### Linux

USB target matching avoids the `serial` attribute. For a matched USB device, CompatForge looks only at matching interface directories, resolves the driver symlink to its basename, and reads `/sys/module/<driver>/version` when that module publishes a version. The raw sysfs path is not emitted.

### macOS

CompatForge intentionally does not infer a per-device driver version from broader system-extension or I/O Registry state. Target presence remains allowlisted from System Information, and `driver_metadata_status` is `unavailable` when no privacy-reviewed driver record can be produced.

## Packaged local snapshot and Schemas

The Python package and standalone executable bundle:

- a compact projection of reviewed compatibility observations and support statements;
- the public JSON Schema contracts required to validate diagnostics, explanations, and handoffs.

CI requires the packaged schema copies to match the public `schemas/` directory exactly and verifies that the packaged local snapshot matches reviewed repository evidence. This allows a frozen binary to work without a source checkout.

Every local explanation includes the packaged snapshot SHA-256 and record counts. A released CLI can therefore lag the website without hiding which reviewed snapshot it used.

## Local explanation semantics

`compatforge-hw explain` reuses the same deterministic resolver as the web/data layers. It preserves:

- observed compatibility versus vendor support as separate answers;
- exact, host-relaxed, and OS-version-relaxed specificity;
- conflicting and unknown states;
- strict architecture/OS/connection-path boundaries;
- source URLs and evidence limitations.

If target collection failed or the requested device was not observed, the command produces no compatibility result. If the connection path is `unspecified`, it does not infer direct-port or hub compatibility.

## Explicit contribution handoff

Phase 5C adds a local export boundary, not a submission client:

```bash
compatforge-hw prepare-contribution \
  --diagnostic diagnostic.json \
  --explanation explanation.json \
  --approve-export \
  --output contribution-handoff.json
```

Without `--approve-export`, the command fails. The generated record is marked `user_approved_export: true` and `evidence_ready: false`. It contains safe configuration context plus the local resolver state, but it does not contain an observed user outcome, reproduction steps, or publication approval.

The handoff is never uploaded by Phase 5C. Phase 6 must introduce any authenticated submission/review path as a separate user action.

## Standalone release verification

The release workflow builds natively for Linux, Windows, and macOS on x86_64 and arm64. Each platform archive gets an SPDX SBOM and, outside pull requests, GitHub provenance and SBOM attestations. Pull requests only build and smoke-test the artifacts.

See [`CLI_RELEASE.md`](CLI_RELEASE.md) for target assets, checksum/attestation verification, release-tag gates, and the distinction between GitHub provenance and OS-vendor code signing.

## Current limitations

- direct-versus-hub classification remains reliable only on Linux; Windows/macOS emit `unspecified`;
- macOS driver-version collection remains intentionally unavailable;
- collected driver metadata is context-only and does not participate in resolver matching;
- Phase 5C provenance attestations are not Apple notarization or Windows Authenticode;
- the contribution handoff is local context only; no submission/upload path exists in Phase 5.

These limitations are preferable to inventing data, widening local collection, or overstating release signing guarantees.
