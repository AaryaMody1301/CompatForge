# Privacy boundary

CompatForge is designed to require less device data, not more.

## Public web product

The read-only public product does not require a user account or diagnostic upload. Compatibility evidence remains separate from local device inspection.

## Local diagnostic agent

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

The manifest contains explicit privacy flags stating that it is local-only, contains no serial/network identifiers, contains no unrelated USB inventory, and performs no automatic upload. Users can inspect the exact JSON before preparing any other artifact.

## Driver metadata boundary

CompatForge permits only target-scoped driver metadata that is useful to compatibility diagnosis:

- driver name/description;
- driver provider when the OS exposes it safely;
- driver version when the OS exposes it safely.

Windows performs VID/PID filtering inside PowerShell before driver properties are returned, and raw PnP instance IDs never enter the manifest. Linux emits only a driver symlink basename and optional module version; it does not emit the sysfs path. macOS driver metadata remains unavailable rather than broadening collection into system-extension or I/O Registry inventories.

A driver string containing control characters or exceeding the collector's bounded metadata length is discarded.

## Local snapshot and resolver

The packaged compatibility snapshot contains reviewed public evidence, not private machine data. `compatforge-hw explain` consumes an already inspectable diagnostic manifest and the packaged snapshot entirely locally. It performs no network call and no upload.

The derived explanation is a separate record from the diagnostic manifest. This keeps locally observed machine facts separate from compatibility claims and source evidence.

## Phase 5C contribution handoff

`compatforge-hw prepare-contribution` is a local export operation, not a submission operation. It requires `--approve-export`; without that flag it fails rather than writing the handoff.

The handoff is allowlisted again instead of copying the entire diagnostic. It can contain:

- host manufacturer/model;
- OS family/version/build and CPU architecture;
- requested device ID and target-present state;
- safe connection classes;
- safe target driver name/provider/version;
- local resolver states and evidence record IDs;
- the local snapshot SHA-256.

It explicitly excludes serial numbers, network identifiers, unrelated USB inventory, raw instance/topology identifiers, and arbitrary native-command output. It contains `automatic_upload: false`, `network_request_performed: false`, and `evidence_ready: false`.

Phase 5C has no network client that can send this record. A user may inspect, retain, or delete the local JSON. A future Phase 6 contribution still requires a separate authenticated action plus user-supplied outcome/reproduction evidence and moderation before publication.

## Release provenance boundary

GitHub build/SBOM attestations describe how downloadable archives were built. They contain build provenance, not user diagnostic data. Release SBOMs describe shipped software components, not a user's machine inventory.

GitHub provenance does not imply Apple notarization or Windows Authenticode signing. CompatForge must not instruct users to bypass operating-system security controls when those signing mechanisms are required by local policy.

## Public evidence

Evidence URLs and source excerpts may be public. Personal data from issue threads or community reports must not be copied into the normalized compatibility dataset unless it is essential to the technical evidence and legally appropriate to retain.
