export const compatibilityOutcomes = [
  "works",
  "works_with_conditions",
  "fails",
  "conflicting",
  "unknown",
] as const;

export const evidenceTypes = [
  "vendor_documentation",
  "independent_reproduction",
  "diagnostic_report",
  "issue_report",
  "community_report",
] as const;

export type CompatibilityOutcome = (typeof compatibilityOutcomes)[number];
export type EvidenceType = (typeof evidenceTypes)[number];
