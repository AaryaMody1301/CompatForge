# Privacy boundary

CompatForge is designed to require less device data, not more.

## Phase 1

There is no telemetry, account system, diagnostic upload, analytics SDK or tracking pixel in the Phase 1 implementation.

## Planned diagnostic-agent rules

A future local diagnostic agent must exclude by default:

- serial numbers;
- usernames;
- hostnames;
- MAC addresses;
- IP addresses;
- Wi-Fi identifiers;
- filesystem paths containing user identity;
- unrelated connected-device inventory.

Before any community submission is sent, users must be able to inspect the exact structured payload.

## Public evidence

Evidence URLs and source excerpts may be public. Personal data from issue threads or community reports must not be copied into the normalized compatibility dataset unless it is essential to the technical evidence and legally appropriate to retain.
