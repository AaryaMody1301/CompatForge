# Third-party notices

## USB ID Repository

CompatForge can ingest the generated `usb.ids` database from the USB ID Repository at `https://usb-ids.gowdy.us/`.

The upstream generated database is distributed under either **GPL-2.0-or-later** or **BSD-3-Clause** terms. CompatForge records the selected source URL, declared upstream license, retrieval timestamp, content SHA-256, parser version, and upstream cache metadata in each source manifest.

CompatForge does not treat USB registry identity records as compatibility evidence.

## Vendor compatibility documentation

Phase 3 includes manually reviewed support statements derived from official vendor documentation. The repository stores source URLs, titles, review timestamps, limitations, and short project-authored paraphrases of technical support facts. It does not mirror or reproduce vendor documentation.

Reviewed sources include Saleae support documentation, Saleae's official support forum, and FTDI driver documentation. The source remains authoritative for its current support policy; CompatForge records when each statement was reviewed so stale evidence can be identified.

## Public community reproductions

Phase 3B may record configuration-level outcomes reported in public engineering/project discussions when the report includes enough technical detail to be useful. The repository stores a URL, title, structured configuration facts, limitations, and a project-authored summary; it does not copy the discussion text.

The first such record references the public `avrdudes/avrdude` Windows-on-ARM64 discussion. Its connection path is explicitly stored as `unspecified` because the source does not state whether a hub, dock, or direct USB port was used.

## Redistribution boundary

The Git repository contains synthetic fixtures for deterministic tests and curated factual evidence metadata. Scheduled live USB registry refreshes are uploaded as review artifacts rather than committed automatically. Any future published third-party data snapshot must preserve its source manifest and applicable attribution/license notices.
