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
- unrelated connected-device inventory.

The CLI requires either a specific target USB VID/PID or `--host-only`. There is deliberately no default full-device inventory mode.

The manifest contains explicit privacy flags stating that it is local-only, contains no serial/network identifiers, contains no unrelated USB inventory, and performs no automatic upload. Users can inspect the exact JSON before any future contribution workflow is introduced.

On macOS, the native System Information command can return more local fields than CompatForge needs. The parser uses a strict allowlist and only transfers target VID/PID presence into the manifest; extra native-command fields are discarded and never logged or written by CompatForge. Linux avoids opening USB serial attributes entirely. Windows filters the target VID/PID inside PowerShell before returning JSON and does not return raw PnP instance IDs.

## Future submission boundary

Any future community contribution must be a separate, explicit user action after manifest inspection. Raw private diagnostics must not become public evidence automatically.

## Public evidence

Evidence URLs and source excerpts may be public. Personal data from issue threads or community reports must not be copied into the normalized compatibility dataset unless it is essential to the technical evidence and legally appropriate to retain.
