import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import communitySubmissionSchema from "../../../../schemas/community-submission.schema.json";

import { devices } from "@/lib/catalog";

const OS_FAMILIES = new Set(["windows", "macos", "ubuntu", "linux", "unknown"]);
const ARCHITECTURES = new Set(["x86_64", "arm64", "unknown"]);
const CONNECTION_PATHS = new Set(["direct_port", "usb_hub", "unspecified"]);
const OUTCOMES = new Set(["works", "works_with_conditions", "fails"]);
const DEVICE_IDS = new Set(devices.map((device) => device.id));
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const TIMEZONE_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i;

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validateCommunitySubmission = ajv.compile(communitySubmissionSchema);

export class SubmissionFormError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function text(formData: FormData, name: string, maxLength: number, required = true) {
  const entry = formData.get(name);
  const value = typeof entry === "string" ? entry.trim() : "";
  if (required && !value) {
    throw new SubmissionFormError("missing_field", `${name} is required`);
  }
  if (value.length > maxLength) {
    throw new SubmissionFormError("field_too_long", `${name} is too long`);
  }
  return value;
}

function enumValue(formData: FormData, name: string, values: Set<string>) {
  const value = text(formData, name, 100);
  if (!values.has(value)) {
    throw new SubmissionFormError("invalid_choice", `${name} has an unsupported value`);
  }
  return value;
}

function lines(value: string, maxItems: number, maxLength: number) {
  const items = value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (items.length > maxItems) {
    throw new SubmissionFormError("too_many_items", `At most ${maxItems} items are allowed`);
  }
  if (items.some((item) => item.length > maxLength)) {
    throw new SubmissionFormError("field_too_long", "One of the list items is too long");
  }
  return [...new Set(items)];
}

function isoTimestamp(value: string) {
  if (!TIMEZONE_PATTERN.test(value)) {
    throw new SubmissionFormError(
      "invalid_timestamp",
      "observed_at must include Z or an explicit UTC offset",
    );
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new SubmissionFormError("invalid_timestamp", "observed_at is not a valid timestamp");
  }
  if (date.getTime() > Date.now() + 5 * 60 * 1000) {
    throw new SubmissionFormError("future_timestamp", "observed_at cannot be in the future");
  }
  return date.toISOString();
}

function referenceUrls(raw: string) {
  const references = lines(raw, 5, 2000);
  for (const reference of references) {
    let url: URL;
    try {
      url = new URL(reference);
    } catch {
      throw new SubmissionFormError("invalid_reference", "References must be valid URLs");
    }
    if (url.protocol !== "https:") {
      throw new SubmissionFormError("invalid_reference", "References must use HTTPS");
    }
  }
  return references;
}

export type CommunitySubmission = {
  record_type: "community_evidence_submission";
  schema_version: "1.0.0";
  client_submission_id: string;
  prepared_at: string;
  evidence_ready: false;
  target_device_id: string;
  handoff: {
    schema_version: "1.0.0";
    sha256: string;
    user_approved_export: true;
  };
  configuration: {
    host: { manufacturer?: string; model?: string };
    operating_system: { family: string; version: string; build?: string };
    architecture: string;
    connection_path: string;
    drivers: Array<{ name?: string; provider?: string; version?: string }>;
  };
  reproduction: {
    outcome: string;
    observed_at: string;
    steps_summary: string;
    conditions: string[];
    limitations: string[];
    firmware_version?: string;
    software_version?: string;
  };
  publication: { anonymized_publication: true; consent_version: "1.0" };
  privacy: {
    contains_raw_diagnostic: false;
    contains_serial_numbers: false;
    contains_network_identifiers: false;
    contains_unrelated_usb_inventory: false;
    automatic_publication: false;
  };
  references: string[];
};

export function parseCommunitySubmission(formData: FormData): CommunitySubmission {
  const deviceId = text(formData, "target_device_id", 32);
  if (!DEVICE_IDS.has(deviceId)) {
    throw new SubmissionFormError("invalid_device", "Select a reviewed CompatForge device");
  }

  const handoffSha = text(formData, "handoff_sha256", 64).toLowerCase();
  if (!SHA256_PATTERN.test(handoffSha)) {
    throw new SubmissionFormError("invalid_handoff", "Handoff SHA-256 must be 64 hex characters");
  }

  const outcome = enumValue(formData, "outcome", OUTCOMES);
  const conditions = lines(text(formData, "conditions", 20000, false), 20, 1000);
  if (outcome === "works_with_conditions" && conditions.length === 0) {
    throw new SubmissionFormError(
      "conditions_required",
      "Conditional outcomes require at least one condition",
    );
  }

  const limitations = lines(text(formData, "limitations", 20000), 20, 1000);
  if (limitations.length === 0) {
    throw new SubmissionFormError("limitations_required", "At least one limitation is required");
  }

  const stepsSummary = text(formData, "steps_summary", 4000);
  if (stepsSummary.length < 20) {
    throw new SubmissionFormError(
      "steps_too_short",
      "Reproduction steps must contain at least 20 characters",
    );
  }

  if (formData.get("anonymized_publication") !== "yes") {
    throw new SubmissionFormError(
      "consent_required",
      "Anonymized-publication consent is required",
    );
  }

  const hostManufacturer = text(formData, "host_manufacturer", 200, false);
  const hostModel = text(formData, "host_model", 200, false);
  const osBuild = text(formData, "os_build", 100, false);
  const driverName = text(formData, "driver_name", 200, false);
  const driverProvider = text(formData, "driver_provider", 200, false);
  const driverVersion = text(formData, "driver_version", 200, false);
  const firmwareVersion = text(formData, "firmware_version", 200, false);
  const softwareVersion = text(formData, "software_version", 200, false);

  const host: CommunitySubmission["configuration"]["host"] = {};
  if (hostManufacturer) host.manufacturer = hostManufacturer;
  if (hostModel) host.model = hostModel;

  const drivers: CommunitySubmission["configuration"]["drivers"] = [];
  if (driverName || driverProvider || driverVersion) {
    drivers.push({
      ...(driverName ? { name: driverName } : {}),
      ...(driverProvider ? { provider: driverProvider } : {}),
      ...(driverVersion ? { version: driverVersion } : {}),
    });
  }

  const submission: CommunitySubmission = {
    record_type: "community_evidence_submission",
    schema_version: "1.0.0",
    client_submission_id: crypto.randomUUID(),
    prepared_at: new Date().toISOString(),
    evidence_ready: false,
    target_device_id: deviceId,
    handoff: {
      schema_version: "1.0.0",
      sha256: handoffSha,
      user_approved_export: true,
    },
    configuration: {
      host,
      operating_system: {
        family: enumValue(formData, "os_family", OS_FAMILIES),
        version: text(formData, "os_version", 100),
        ...(osBuild ? { build: osBuild } : {}),
      },
      architecture: enumValue(formData, "architecture", ARCHITECTURES),
      connection_path: enumValue(formData, "connection_path", CONNECTION_PATHS),
      drivers,
    },
    reproduction: {
      outcome,
      observed_at: isoTimestamp(text(formData, "observed_at", 100)),
      steps_summary: stepsSummary,
      conditions,
      limitations,
      ...(firmwareVersion ? { firmware_version: firmwareVersion } : {}),
      ...(softwareVersion ? { software_version: softwareVersion } : {}),
    },
    publication: { anonymized_publication: true, consent_version: "1.0" },
    privacy: {
      contains_raw_diagnostic: false,
      contains_serial_numbers: false,
      contains_network_identifiers: false,
      contains_unrelated_usb_inventory: false,
      automatic_publication: false,
    },
    references: referenceUrls(text(formData, "references", 12000, false)),
  };

  if (!validateCommunitySubmission(submission)) {
    throw new SubmissionFormError(
      "schema_validation_failed",
      "Submission did not satisfy the public community JSON Schema",
    );
  }

  return submission;
}
