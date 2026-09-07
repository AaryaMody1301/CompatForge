# Source policy

A source adapter may enter CompatForge only when all of the following are documented:

1. canonical upstream URL and owner/maintainer;
2. redistribution/license terms;
3. automated-access expectations and a conservative refresh cadence;
4. exact raw-content checksum;
5. parser name/version;
6. explicit mapping from raw records to CompatForge entities;
7. regression fixtures that do not depend on the network;
8. failure behavior for malformed, duplicate, or unexpectedly empty input.

Scheduled refreshes must never auto-commit upstream data to `main`. They produce reviewable artifacts. Publishing a dataset remains an explicit release action.
