import type { MetadataRoute } from "next";

import { catalogSource, devices } from "@/lib/catalog";
import { observations, supportStatements } from "@/lib/evidence";
import { SITE_URL } from "@/lib/site";
import { getCommunityFeatureState } from "@/lib/supabase/config";

const evidenceDeviceIds = new Set([
  ...supportStatements.map((statement) => statement.device_id),
  ...observations.map((observation) => observation.device_id),
]);
const indexableDevices = devices.filter(
  (device) => device.reviewed_metadata || evidenceDeviceIds.has(device.id),
);

function latestDate(values: string[]) {
  if (values.length === 0) return undefined;
  return new Date([...values].sort().at(-1) as string);
}

const catalogDate = catalogSource.snapshot_date
  ? `${catalogSource.snapshot_date}T00:00:00Z`
  : null;
const evidenceDates = [
  ...supportStatements.map((statement) => statement.reviewed_at),
  ...observations.map((observation) => observation.observed_at),
];
const siteLastModified = latestDate(
  [...evidenceDates, catalogDate].filter((value): value is string => value !== null),
);

function deviceLastModified(deviceId: string) {
  return latestDate([
    ...supportStatements
      .filter((statement) => statement.device_id === deviceId)
      .map((statement) => statement.reviewed_at),
    ...observations
      .filter((observation) => observation.device_id === deviceId)
      .map((observation) => observation.observed_at),
    ...(catalogDate ? [catalogDate] : []),
  ]);
}

export default function sitemap(): MetadataRoute.Sitemap {
  const topLevel = [
    { path: "/", priority: 1 },
    { path: "/check", priority: 0.9 },
    { path: "/devices", priority: 0.9 },
    { path: "/coverage", priority: 0.7 },
    { path: "/methodology", priority: 0.6 },
  ];

  if (getCommunityFeatureState() === "ready") {
    topLevel.push({ path: "/submissions", priority: 0.5 });
  }

  return [
    ...topLevel.map(({ path, priority }) => ({
      url: `${SITE_URL}${path}`,
      lastModified: siteLastModified,
      changeFrequency: "weekly" as const,
      priority,
    })),
    ...indexableDevices.map((device) => ({
      url: `${SITE_URL}/devices/${device.slug}`,
      lastModified: deviceLastModified(device.id),
      changeFrequency: "monthly" as const,
      priority: device.reviewed_metadata ? 0.7 : 0.4,
    })),
  ];
}
