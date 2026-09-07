# Local diagnostic agent

Phase 5 adds an inspectable, local-only diagnostic manifest. The agent does not upload data and does not attempt to fix, enable, disable, flash, or reconfigure hardware.

## Commands

Collect host/OS metadata only:

```bash
compatforge-diagnose --host-only --output compatforge-diagnostic.json
```

Collect host metadata plus one known target peripheral:

```bash
compatforge-diagnose --device usb:0403:6001 --output compatforge-diagnostic.json
```

Use `--output -` to inspect the JSON directly on stdout.

## Privacy model

The diagnostic contract is allowlist-based. The generated manifest can contain:

- OS family/name/version/build;
- CPU architecture;
- host manufacturer/model;
- the requested USB VID/PID identity;
- whether that target was observed;
- a safe target count;
- connection class when it can be inferred safely;
- USB link speed when available.

It does not contain serial numbers, usernames, hostnames, MAC addresses, IP addresses, Wi-Fi identifiers, filesystem paths, or unrelated USB inventory. There is no automatic upload path.

The command requires either a specific canonical device ID or `--host-only`; there is deliberately no "dump every connected USB device" mode.

## OS collectors

### Windows

Host information comes from CIM (`Win32_ComputerSystem` and `Win32_OperatingSystem`). Target presence comes from `Get-PnpDevice -PresentOnly`. The PowerShell collector filters the target VID/PID before returning JSON to Python and does not return the raw PnP instance ID, which can contain a device serial.

### macOS

Host model comes from `sysctl hw.model`; OS/architecture come from Python platform APIs. Target USB identity comes from `system_profiler SPUSBDataType -json`. The parser is strict: only VID/PID-derived target presence enters the diagnostic manifest. Other fields returned locally by System Information, including serial data, are discarded and never logged or written by CompatForge.

### Linux

Distribution information comes from `/etc/os-release` through Python's standard library. Host manufacturer/model use the non-serial DMI sysfs fields. USB target matching reads `idVendor`, `idProduct`, and optionally `speed` from `/sys/bus/usb/devices`; it never opens the USB `serial` attribute. Linux topology names are used only to classify a target as direct-port versus behind a USB hub; the raw topology path is not emitted.

## Current limitations

- driver-version collection is deferred until each OS has a privacy-reviewed implementation;
- direct-versus-hub classification is currently reliable only on Linux; Windows/macOS emit `unspecified`;
- the manifest does not yet perform a local resolver lookup against a packaged CompatForge snapshot;
- there is no submission/upload flow in Phase 5A.

Those limitations are preferable to inventing data or collecting identifiers that the compatibility resolver does not yet require.
