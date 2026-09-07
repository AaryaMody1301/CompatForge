# Privacy boundary

CompatForge is designed to require less device data, not more.

## Public web product

The read-only public product does not require a user account or diagnostic upload. Compatibility evidence remains separate from local device inspection.

## Phase 5 local diagnostic agent

The diagnostic agent is local-only and allowlist-based. It excludes from the generated manifest:

- serial numbers;
- usernames;
- hostnames;
- MAC addresses;
- IP addresses;
- Wi-Fi identifiers;
- filesystem paths containing user identity;
- raw Windows PnP instance IDs;
- raw USB topology paths;
- unrelated connected-device inventory.

The CLI requires either a specific target USB VID/PID or `--host-only`. There is deliberately no default full-device inventory mode.

The manifest contains explicit privacy flags stating that it is local-only, contains no serial/network identifiers, contains no unrelated USB inventory, and performs no automatic upload. Users can inspect the exact JSON before any future contribution workflow is introduced.

## Driver metadata boundary

Phase 5B permits only target-scoped driver metadata that is useful to compatibility diagnosis:

- driver name/description;
- driver provider when the OS exposes it safely;
- driver version when the OS exposes it safely.

Windows performs VID/PID filtering inside PowerShell before any driver properties are returned, and raw PnP instance IDs never enter the manifest. Linux emits only a driver symlink basename and optional module version; it does not emit the sysfs path. macOS driver metadata remains unavailable rather than broadening collection into system-extension or I/O Registry inventories.

A driver string containing control characters or exceeding the collector's bounded metadata length is discarded.

## Local snapshot and resolver

The packaged compatibility snapshot contains reviewed public evidence, not private machine data. `compatforge-explain` consumes an already inspectable diagnostic manifest and the packaged snapshot entirely locally. It performs no network call and no upload.

The derived explanation is a separate record from the diagnostic manifest. This keeps locally observed machine facts separate from compatibility claims and source evidence.

## Future submission boundary

Any future community contribution must be a separate, explicit user action after manifest inspection. Raw private diagnostics must not become public evidence automatically.

## Public evidence

Evidence URLs and source excerpts may be public. Personal data from issue threads or community reports must not be copied into the normalized compatibility dataset unless it is essential to the technical evidence and legally appropriate to retain.
