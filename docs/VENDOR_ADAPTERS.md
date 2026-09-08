# Vendor adapters and semantic change reports

Phase 7B adds source-specific, read-only vendor adapters on top of the Phase 7A freshness review workflow.

The purpose is narrow: detect when reviewed vendor facts may have changed without copying vendor pages into the repository and without automatically changing CompatForge evidence.

## Trust boundary

Vendor adapter output is review input, not compatibility evidence.

An adapter may:

- fetch one explicitly permitted HTTPS source;
- follow redirects only when the final host remains on the adapter's exact allowlisted host;
- read at most 2 MiB per source;
- extract a small set of reviewed compatibility facts;
- hash those semantic facts;
- compare them with a version-controlled reviewed baseline;
- produce a change report and workflow artifact.

An adapter may not:

- crawl arbitrary vendor pages;
- follow a redirect onto another host;
- mirror or republish the vendor page;
- rewrite `data/evidence/`;
- change a support status or compatibility outcome;
- publish community evidence;
- write Supabase state;
- push a commit or open a publication PR by itself.

## Initial permitted adapters

### `ftdi_vcp`

Source: `https://ftdichip.com/drivers/vcp-drivers/`

Reviewed semantic facts:

- Windows Desktop release date;
- Windows Desktop x64 VCP version;
- Windows Desktop ARM64 VCP version;
- Windows Universal ARM64 VCP version;
- presence of FTDI's ARM64 installer limitation.

The reviewed baseline is `data/sources/vendor-adapters/ftdi_vcp.json`.

### `saleae_supported_os`

Source: `https://www.saleae.com/support/logic-software/download-and-installation/supported-operating-systems`

Reviewed semantic facts:

- general Logic 2 Windows versions and architecture declaration;
- macOS Apple-silicon declaration;
- Ubuntu 64-bit declaration.

The reviewed baseline is `data/sources/vendor-adapters/saleae_supported_os.json`.

Saleae's general supported-OS page currently describes Windows 10 and 11 as x64. CompatForge also has separately scoped vendor evidence about Windows ARM64 through Saleae's Insider Build channel. The adapter does not collapse those claims together. A difference between general support and a separately scoped Insider statement is a review signal, not an automatic contradiction.

## Semantic baselines

Each baseline stores only:

- adapter name;
- source URL;
- review date;
- the small extracted facts object;
- SHA-256 of the canonical facts object;
- a note that the vendor page itself is not mirrored.

Raw response hashes, ETag values and Last-Modified values are operational metadata only. They can change because of templates, analytics or CDN behavior and are therefore not used to decide whether compatibility semantics changed.

## Change reports

`python -m compatforge_pipeline.vendor_adapters snapshot` fetches all permitted adapters and writes a live semantic snapshot.

`python -m compatforge_pipeline.vendor_adapters compare` compares that snapshot with the reviewed baselines and reports each source as:

- `unchanged`;
- `changed`, with the exact semantic fields that differ;
- `missing_baseline`.

The weekly evidence workflow uploads the snapshot and change report together with the Phase 7A freshness artifacts. It does not fail merely because a semantic delta exists; the report is intended to drive human review and the later stale-evidence workflow.

## Updating a baseline

A baseline should change only after a reviewer:

1. opens the vendor source directly;
2. confirms the adapter still extracts the intended facts;
3. decides whether canonical support statements need a separate reviewed edit;
4. updates the baseline facts and semantic SHA-256 in the same reviewed pull request;
5. keeps any evidence modification separate and explicit enough to inspect in the diff.

A baseline update is not evidence publication by itself.

## Next slice

Phase 7C can use accepted community candidates to prepare bounded pull requests, but it must preserve the Phase 6C candidate SHA-256, code-review, CI, merge and publication-receipt gates. Vendor adapters remain read-only inputs to that process.
