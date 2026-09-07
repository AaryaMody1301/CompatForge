# Compatibility evidence

This directory contains manually reviewed compatibility evidence records.

## Evidence classes

- `compatibility_observation`: an exact or reproduced configuration-level result.
- `compatibility_support_statement`: a scoped vendor/support statement that documents support without claiming that CompatForge reproduced the result on a specific host.

Vendor support statements are intentionally kept separate from observations. A vendor-supported configuration can still have a CompatForge claim state of `unknown` when no exact or relaxed observation exists.

## Review rule

A support statement must point to the original HTTPS source, paraphrase rather than copy source text, state its target scope, include limitations, and record when CompatForge reviewed it.

The initial Phase 3 corpus uses official Saleae and FTDI documentation only. These records are evidence inputs, not scraped mirrors of the source pages.
