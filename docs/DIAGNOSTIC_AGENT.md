# Local diagnostic agent

Phase 5 provides an inspectable, local-only diagnostic workflow. The agent does not upload data and does not attempt to fix, enable, disable, flash, or reconfigure hardware.

## Commands

Collect host/OS metadata only:

```bash
compatforge-diagnose --host-only --output compatforge-diagnostic.json
```

Collect host metadata plus one known target peripheral:

```bash
compatforge-diagnose --device usb:0403:6001 --output compatforge-diagnostic.json
```

Inspect the packaged local compatibility snapshot:

```bash
compatforge-snapshot info
```

Resolve a previously inspected target diagnostic entirely offline:

```bash
compatforge-explain \
  --diagnostic compatforge-diagnostic.json \
  --output compatforge-explanation.json
```

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

Target presence comes from `Get-PnpDevice -PresentOnly`. Filtering by VID/PID happens inside PowerShell before JSON is returned to Python. For matching instances only, the collector reads the Windows device properties for driver description, provider, and version. The raw PnP instance ID is used locally for the property lookup but is never returned to Python or written into the manifest.

Windows documents `DEVPKEY_Device_DriverVersion` as the installed device-instance driver version and provides corresponding driver description/provider properties through the same device-property model.

### Linux

USB target matching still avoids the `serial` attribute. For a matched USB device, CompatForge looks only at matching interface directories, resolves the driver symlink to its basename, and reads `/sys/module/<driver>/version` when that module publishes a version. The raw sysfs path is not emitted.

Linux kernel documentation notes that `/sys/module/<MODULENAME>/version` exists when the module provides `MODULE_VERSION`; absence is therefore treated as partial metadata rather than a failure.

### macOS

Phase 5B intentionally does not attempt to infer a per-device driver version from broader system-extension or I/O Registry state. Target presence remains allowlisted from System Information, and `driver_metadata_status` is `unavailable` when no privacy-reviewed driver record can be produced.

## Driver metadata status

A target contains one of:

- `collected` - driver records were found and each has a version;
- `partial` - safe driver records were found but at least one version is unavailable;
- `unavailable` - the target is present, but no privacy-reviewed driver record is available;
- `not_observed` - the target was not present.

Driver metadata is context-only in Phase 5B. It is displayed in the local explanation but does not silently tighten or broaden resolver matching.

## Packaged local snapshot

`compatforge-hw-pipeline` bundles a compact projection of the reviewed compatibility observations and vendor-support statements. The projection contains only fields needed for local resolution and evidence/source explanation.

CI rebuilds that projection from `data/evidence/` and requires byte-equivalent canonical content before merge. `compatforge-snapshot verify` is the same drift check available to developers.

The snapshot can lag the website until a newer CLI package is released. Every local explanation therefore includes the packaged snapshot SHA-256 and record counts.

## Local explanation semantics

`compatforge-explain` reuses the same deterministic resolver as the web/data layers. It preserves:

- observed compatibility versus vendor support as separate answers;
- exact, host-relaxed, and OS-version-relaxed specificity;
- conflicting and unknown states;
- strict architecture/OS/connection-path boundaries;
- source URLs and evidence limitations.

If target collection failed or the requested device was not observed, the command produces no compatibility result. If the connection path is `unspecified`, it does not infer direct-port or hub compatibility.

## Current limitations

- direct-versus-hub classification remains reliable only on Linux; Windows/macOS emit `unspecified`;
- macOS driver-version collection remains intentionally unavailable;
- collected driver metadata does not yet participate in resolver matching;
- signed/packageable standalone binaries are deferred to Phase 5C;
- there is no submission/upload flow in Phase 5B.

These limitations are preferable to inventing data or widening local collection beyond the resolver's current needs.
