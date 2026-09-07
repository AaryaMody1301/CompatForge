# Evidence model

## Observation, support statement, and claim

CompatForge separates three concepts that are often incorrectly collapsed into one compatibility flag.

An **observation** records the outcome of a specific tested or reported configuration. It includes the device, host, architecture, OS version, connection path, source, and timestamps.

A **support statement** records a scoped statement from a vendor or support source. It can say that a device/driver/software combination is supported for an OS or architecture without pretending that CompatForge reproduced the result on a specific laptop.

A **claim** is a deterministic resolver output generated from observations for a requested configuration. Support state is returned beside the claim rather than being silently converted into a successful observation.

## Observation outcomes

Individual observations support three outcomes:

- `works`
- `works_with_conditions`
- `fails`

`conflicting` and `unknown` are claim states, not single-observation outcomes.

## Support states

Individual support statements use:

- `supported`
- `supported_with_conditions`
- `unsupported`

The resolver can additionally return `conflicting` or `unknown` when multiple equally specific statements disagree or no statement matches.

## Evidence source types

Observations may use:

- `vendor_documentation`
- `independent_reproduction`
- `diagnostic_report`
- `issue_report`
- `community_report`

Support statements currently accept `vendor_documentation` and `issue_report`.

Source type is metadata. It is not an opaque numeric trust score.

## Conflict handling

If equally specific observations disagree between success and failure, the resolver preserves every observation and returns `conflicting`. It does not average evidence into a probability.

## Specificity and unknown connection paths

A result for Windows 11 x86-64 through a direct port is not automatically a result for Windows 11 ARM64 or a USB hub. The resolver may relax host model and then OS version, but it never relaxes architecture, OS family, or connection path. Every relaxation is explicit in the resolver output.

Phase 3B allows an observation connection kind of `unspecified` only when a credible source does not document the physical path. Such an observation is preserved for provenance and coverage but does not match a query for `direct_port`, `usb_hub`, `dock`, or another specific path. CompatForge therefore prefers an explicit unknown over an invented connection topology.

## Freshness

`observed_at` is when an observation occurred or was documented. `recorded_at` is when CompatForge recorded it.

Support statements use `reviewed_at` to record when CompatForge last checked the source and `recorded_at` for when the record entered the corpus. Source freshness and record creation time are not interchangeable.

The analytical layer classifies evidence as `fresh` (up to 180 days), `aging` (181-365 days), or `stale` (more than 365 days) relative to an explicit snapshot `as_of` timestamp. Freshness metadata never rewrites the underlying outcome/support state.
