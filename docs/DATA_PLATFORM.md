# Hardware identity data platform

## Boundary

The Phase 2 data platform answers **what hardware identity is this?** It does not answer whether the hardware works with a host. USB registry data can never create a `WORKS`, `FAILS`, `CONFLICTING`, or `UNKNOWN` compatibility result.

## Pipeline

```text
usb.ids source snapshot
        |
        v
raw/<sha256>.usb.ids
        |
        v
Python parser + identity normalization
        |
        +--> source_manifest.json
        |
        v
DuckDB bronze.usb_vendors / bronze.usb_devices
        |
        +--> Bronze Parquet
        |
        v
dbt staging
        |
        v
dbt intermediate identity join
        |
        v
analytics.device_catalog
        |
        +--> device_catalog.jsonl
        +--> device_catalog.parquet
        +--> snapshot_manifest.json
```

## Provenance requirements

Every source build records the original source URL, upstream homepage, source license, retrieval time, upstream Last-Modified/ETag when available, parser version, SHA-256, row counts, and raw/bronze artifact locations.

The raw source file is named by content SHA-256. A changed upstream payload therefore creates a new immutable raw identity.

## Reproducibility

CI builds the same synthetic fixture twice from an identical retrieval timestamp, runs dbt twice, exports both public snapshots, and requires the complete snapshot manifests to match exactly. The public manifest contains both JSONL and Parquet hashes plus a canonical snapshot hash.

## Public serving contract

`device_catalog` contains only identity fields:

- `device_id`;
- `vendor_id`;
- `vendor_name`;
- `product_id`;
- `product_name`;
- `interface_type`;
- `identity_source`;
- `source_sha256`.

Compatibility evidence enters a separate model in Phase 3.

## Refresh policy

The scheduled workflow checks the upstream USB ID Repository at most once per day and uploads a candidate artifact. It does not automatically commit or publish upstream changes. A candidate must pass parsing, dbt tests, source provenance checks, and snapshot export before it can be reviewed for release.
