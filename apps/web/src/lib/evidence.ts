import {
  canonicalObservationDocuments,
  canonicalSupportStatementDocuments,
} from "./evidence.generated";

export const architectures = ["x86_64", "arm64"] as const;
export const osFamilies = ["windows", "macos", "ubuntu"] as const;
export const connectionKinds = [
  "direct_port",
  "usb_hub",
  "adapter",
  "dock",
  "unspecified",
] as const;

export type Architecture = (typeof architectures)[number];
export type OsFamily = (typeof osFamilies)[number];
export type ConnectionKind = (typeof connectionKinds)[number];
export type ClaimState = "works" | "works_with_conditions" | "fails" | "conflicting" | "unknown";
export type SupportState =
  | "supported"
  | "supported_with_conditions"
  | "unsupported"
  | "conflicting"
  | "unknown";

export type Source = { source_url: string; source_title: string };

export type SupportStatement = {
  statement_id: string;
  device_id: string;
  scope: {
    architecture: Architecture | "any";
    operating_system: {
      family: OsFamily;
      version_mode: "exact" | "one_of" | "minimum" | "any";
      versions?: string[];
      minimum_version?: string;
    };
    connection: {
      kind: ConnectionKind | "any_usb";
      minimum_usb_generation?: string;
    };
  };
  driver?: { name: string; version?: string };
  software?: { name: string; version?: string };
  support_status: "supported" | "supported_with_conditions" | "unsupported";
  conditions?: string[];
  evidence: {
    source_type: "vendor_documentation" | "issue_report";
    sources: Source[];
    source_note: string;
  };
  reviewed_at: string;
  recorded_at: string;
  limitations?: string[];
};

export type Observation = {
  observation_id: string;
  device_id: string;
  host: {
    manufacturer: string;
    model: string;
    architecture: Architecture;
    operating_system: { family: OsFamily; version: string; build?: string };
  };
  connection_path: { kind: ConnectionKind; notes?: string }[];
  driver?: { name: string; version?: string };
  software?: { name: string; version?: string };
  firmware_version?: string;
  outcome: "works" | "works_with_conditions" | "fails";
  conditions?: string[];
  evidence: {
    source_type:
      | "vendor_documentation"
      | "independent_reproduction"
      | "diagnostic_report"
      | "issue_report"
      | "community_report";
    source_url: string;
    source_title: string;
  };
  observed_at: string;
  recorded_at: string;
  limitations?: string[];
  notes?: string;
};

export const supportStatements: readonly SupportStatement[] =
  canonicalSupportStatementDocuments as unknown as readonly SupportStatement[];

export const observations: readonly Observation[] =
  canonicalObservationDocuments as unknown as readonly Observation[];

export type CompatibilityQuery = {
  deviceId: string;
  architecture: Architecture;
  osFamily: OsFamily;
  osVersion: string;
  connectionKind: ConnectionKind;
  hostManufacturer?: string;
  hostModel?: string;
};

function normalize(value: string) {
  return value.trim().toLocaleLowerCase("en");
}

function numericVersion(value: string) {
  if (!/^\d+(?:\.\d+)*$/.test(value.trim())) return null;
  return value.trim().split(".").map(Number);
}

function compareVersions(left: number[], right: number[]) {
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference !== 0) return difference;
  }
  return 0;
}

function versionMatches(statement: SupportStatement, queryVersion: string) {
  const operatingSystem = statement.scope.operating_system;
  if (operatingSystem.version_mode === "any") return true;
  if (operatingSystem.version_mode === "exact" || operatingSystem.version_mode === "one_of") {
    return (operatingSystem.versions ?? []).some(
      (version) => normalize(version) === normalize(queryVersion),
    );
  }
  const minimum = numericVersion(operatingSystem.minimum_version ?? "");
  const current = numericVersion(queryVersion);
  return minimum !== null && current !== null && compareVersions(current, minimum) >= 0;
}

function supportMatches(statement: SupportStatement, query: CompatibilityQuery) {
  if (statement.device_id !== query.deviceId) return false;
  if (!(["any", query.architecture] as string[]).includes(statement.scope.architecture)) return false;
  if (statement.scope.operating_system.family !== query.osFamily) return false;
  if (!versionMatches(statement, query.osVersion)) return false;
  const connection = statement.scope.connection.kind;
  return connection === "any_usb" || connection === query.connectionKind;
}

function supportSpecificity(statement: SupportStatement, query: CompatibilityQuery) {
  let score = statement.scope.architecture === query.architecture ? 4 : 1;
  score += { exact: 4, one_of: 4, minimum: 2, any: 1 }[
    statement.scope.operating_system.version_mode
  ];
  score += statement.scope.connection.kind === "any_usb" ? 1 : 2;
  return score;
}

function bestSupport(query: CompatibilityQuery) {
  const matches = supportStatements.filter((statement) => supportMatches(statement, query));
  if (matches.length === 0) return [];
  const bestScore = Math.max(...matches.map((statement) => supportSpecificity(statement, query)));
  return matches.filter((statement) => supportSpecificity(statement, query) === bestScore);
}

function supportState(statements: readonly SupportStatement[]): SupportState {
  if (statements.length === 0) return "unknown";
  const states = new Set(statements.map((statement) => statement.support_status));
  const positive = states.has("supported") || states.has("supported_with_conditions");
  if (positive && states.has("unsupported")) return "conflicting";
  if (states.has("unsupported")) return "unsupported";
  if (states.has("supported_with_conditions")) return "supported_with_conditions";
  return "supported";
}

function observationMatches(
  observation: Observation,
  query: CompatibilityQuery,
  options: { ignoreHost: boolean; ignoreOsVersion: boolean },
) {
  if (observation.device_id !== query.deviceId) return false;
  if (observation.host.architecture !== query.architecture) return false;
  if (observation.host.operating_system.family !== query.osFamily) return false;
  if (
    observation.connection_path.map((item) => item.kind).join(">") !== query.connectionKind
  ) {
    return false;
  }
  if (
    !options.ignoreOsVersion &&
    normalize(observation.host.operating_system.version) !== normalize(query.osVersion)
  ) {
    return false;
  }
  if (options.ignoreHost) return true;
  if (!query.hostManufacturer || !query.hostModel) return false;
  return (
    normalize(observation.host.manufacturer) === normalize(query.hostManufacturer) &&
    normalize(observation.host.model) === normalize(query.hostModel)
  );
}

function bestObservations(query: CompatibilityQuery) {
  const tiers = [
    { name: "exact", ignoreHost: false, ignoreOsVersion: false },
    { name: "host_relaxed", ignoreHost: true, ignoreOsVersion: false },
    { name: "os_version_relaxed", ignoreHost: true, ignoreOsVersion: true },
  ] as const;

  for (const tier of tiers) {
    const matches = observations.filter((observation) => observationMatches(observation, query, tier));
    if (matches.length > 0) return { observations: matches, specificity: tier.name };
  }
  return { observations: [] as Observation[], specificity: "none" as const };
}

function claimState(matched: readonly Observation[]): ClaimState {
  if (matched.length === 0) return "unknown";
  const outcomes = new Set(matched.map((observation) => observation.outcome));
  const success = outcomes.has("works") || outcomes.has("works_with_conditions");
  if (success && outcomes.has("fails")) return "conflicting";
  if (outcomes.has("fails")) return "fails";
  if (outcomes.has("works_with_conditions")) return "works_with_conditions";
  return "works";
}

function uniqueConditions(records: readonly { conditions?: string[] }[]) {
  return [...new Set(records.flatMap((record) => record.conditions ?? []))].sort();
}

export function resolveCompatibility(query: CompatibilityQuery) {
  const matchedObservations = bestObservations(query);
  const matchedSupport = bestSupport(query);
  return {
    claimState: claimState(matchedObservations.observations),
    specificity: matchedObservations.specificity,
    observations: matchedObservations.observations,
    observationConditions: uniqueConditions(matchedObservations.observations),
    supportState: supportState(matchedSupport),
    supportStatements: matchedSupport,
    supportConditions: uniqueConditions(matchedSupport),
  };
}

export function getDeviceEvidence(deviceId: string) {
  return {
    observations: observations.filter((observation) => observation.device_id === deviceId),
    supportStatements: supportStatements.filter((statement) => statement.device_id === deviceId),
  };
}

export function formatArchitecture(value: Architecture | "any") {
  if (value === "x86_64") return "x86-64";
  if (value === "arm64") return "ARM64";
  return "Any architecture";
}

export function formatOsFamily(value: OsFamily) {
  return { windows: "Windows", macos: "macOS", ubuntu: "Ubuntu" }[value];
}

export function formatConnection(value: ConnectionKind | "any_usb") {
  return {
    any_usb: "Any USB path",
    direct_port: "Direct USB port",
    usb_hub: "USB hub",
    adapter: "Adapter",
    dock: "Dock",
    unspecified: "Unspecified path",
  }[value];
}

export function formatVersionScope(statement: SupportStatement) {
  const os = statement.scope.operating_system;
  if (os.version_mode === "any") return "Any version";
  if (os.version_mode === "minimum") return `${os.minimum_version}+`;
  return (os.versions ?? []).join(", ");
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
}
