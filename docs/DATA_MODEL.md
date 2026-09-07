# Data model

## Device identity

Phase 1 supports canonical USB VID/PID identities:

```text
usb:<VID>:<PID>
```

VID and PID are uppercase, zero-padded four-character hexadecimal values. Example:

```text
usb:0403:6001
```

A USB identity describes a hardware identifier, not a compatibility result. Product names remain descriptive metadata and are not used to infer identity.

## Device

A `device` record contains:

- canonical device ID;
- manufacturer and product name;
- initial device category;
- interface;
- one or more structured hardware identifiers.

The Phase 1 public contract is `schemas/device.schema.json`.

## Compatibility observation

A `compatibility_observation` captures one documented or reproduced result at configuration grain. Required dimensions are:

- device;
- host manufacturer/model;
- CPU architecture;
- OS family/version;
- connection path;
- outcome;
- evidence source;
- observation and recording timestamps.

Driver, firmware, supporting software, conditions and limitations are retained when known.

## Future entities

Later phases will add canonical host models, drivers, firmware, software dependencies, normalized connection components, compatibility claims and claim-to-observation relationships. They are intentionally not frozen in Phase 1.
