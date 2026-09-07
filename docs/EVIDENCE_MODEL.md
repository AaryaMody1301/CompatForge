# Evidence model

## Observation versus claim

An **observation** records what a source documented or what a test actually observed.

A **claim** will be a deterministic conclusion generated from one or more observations for a requested configuration.

CompatForge never rewrites an observation merely because a later claim changes.

## Observation outcomes

Individual observations support three outcomes:

- `works` - the tested/documented configuration worked;
- `works_with_conditions` - it worked only with explicit conditions;
- `fails` - the tested/documented configuration failed.

`conflicting` and `unknown` are future **claim states**, not observation outcomes. A single observation cannot itself prove that the evidence corpus conflicts or is unknown.

## Evidence source types

- `vendor_documentation`
- `independent_reproduction`
- `diagnostic_report`
- `issue_report`
- `community_report`

Source type is metadata. It is not an opaque numeric trust score.

## Conflict handling

If credible observations disagree, later resolver phases must preserve each observation and produce a `conflicting` claim. The system must not average incompatible results into a synthetic confidence number.

## Specificity

A result for Windows 11 x86-64 through a specific USB hub is not automatically a result for Windows 11 ARM64 or a direct connection. Resolver relaxation must be explicit and shown to users.

## Freshness

`observed_at` is when the compatibility fact was observed or documented. `recorded_at` is when CompatForge recorded it. These dates must not be conflated.
