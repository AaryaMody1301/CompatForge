# Third-party notices

## USB ID Repository

CompatForge can ingest the generated `usb.ids` database from the USB ID Repository at `https://usb-ids.gowdy.us/`.

The upstream generated database is distributed under either **GPL-2.0-or-later** or **BSD-3-Clause** terms. CompatForge records the selected source URL, declared upstream license, retrieval timestamp, content SHA-256, parser version, and upstream cache metadata in each source manifest.

CompatForge does not treat USB registry identity records as compatibility evidence.

## Vendor compatibility documentation

Phase 3 introduces manually reviewed support statements derived from official vendor documentation. The repository stores source URLs, titles, review timestamps, limitations, and short project-authored paraphrases of technical support facts. It does not mirror or reproduce vendor documentation.

Initial reviewed sources include Saleae support documentation and FTDI driver documentation. The source remains authoritative for its own current support policy; CompatForge records when each statement was last reviewed so stale evidence can be identified later.

## Redistribution boundary

The Git repository contains synthetic fixtures for deterministic tests and curated factual support metadata. Scheduled live USB registry refreshes are uploaded as review artifacts rather than committed automatically. Any future published third-party data snapshot must preserve its source manifest and applicable attribution/license notices.
