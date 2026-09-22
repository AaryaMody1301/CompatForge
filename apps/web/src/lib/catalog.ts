import publishedUsbCatalog from "../../../../data/catalog/usb-device-catalog.json";
import curatedDeviceMetadata from "../../../../data/catalog/curated-devices.json";

type PublishedCatalog = {
  counts: { devices: number; vendors: number };
  schema_version: number;
  source: {
    homepage: string;
    license: string;
    name: string;
    parser_version: string;
    version: string | null;
    snapshot_date: string | null;
    sha256: string;
    source_url: string;
  };
  vendors: Array<[string, string, Array<[string, string]>]>;
};

type CuratedDevice = {
  id: string;
  slug: string;
  manufacturer: string;
  name: string;
  aliases: string[];
  category: string;
  summary: string;
  identity_source: string;
};

export type Device = CuratedDevice & {
  curated_metadata: boolean;
};

const published = publishedUsbCatalog as unknown as PublishedCatalog;
const curated = curatedDeviceMetadata as readonly CuratedDevice[];
const curatedById = new Map(curated.map((device) => [device.id, device] as const));

function canonicalDeviceId(vendorId: string, productId: string) {
  return `usb:${vendorId.toUpperCase()}:${productId.toUpperCase()}`;
}

function canonicalSlug(deviceId: string) {
  return deviceId.toLocaleLowerCase("en").replaceAll(":", "-");
}

function registryUrl(vendorId: string, productId: string) {
  return `https://usb-ids.gowdy.us/read/UD/${vendorId.toLocaleLowerCase("en")}/${productId.toLocaleLowerCase("en")}`;
}

function normalizeSearch(value: string) {
  return value
    .normalize("NFKD")
    .toLocaleLowerCase("en")
    .replace(/[^a-z0-9:]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export function normalizeDeviceId(value: string) {
  const match = /^usb:([0-9a-f]{4}):([0-9a-f]{4})$/i.exec(value.trim());
  return match ? canonicalDeviceId(match[1], match[2]) : null;
}

const generatedDevices = published.vendors.flatMap(([vendorId, vendorName, products]) =>
  products.map(([productId, productName]) => {
    const id = canonicalDeviceId(vendorId, productId);
    const curatedDevice = curatedById.get(id);
    if (curatedDevice) {
      return { ...curatedDevice, curated_metadata: true } satisfies Device;
    }
    return {
      id,
      slug: canonicalSlug(id),
      manufacturer: vendorName,
      name: productName,
      aliases: [],
      category: "USB device",
      summary:
        "Known USB identity from the USB ID Repository. Compatibility remains unknown until reviewed evidence is available.",
      identity_source: registryUrl(vendorId, productId),
      curated_metadata: false,
    } satisfies Device;
  }),
);

export const devices: readonly Device[] = generatedDevices;
export const curatedDevices: readonly Device[] = devices.filter(
  (device) => device.curated_metadata,
);
export const catalogCounts = published.counts;
export const catalogSource = published.source;

const devicesById = new Map(devices.map((device) => [device.id, device] as const));
const devicesBySlug = new Map<string, Device>();
for (const device of devices) {
  devicesBySlug.set(device.slug, device);
  devicesBySlug.set(canonicalSlug(device.id), device);
}

export function getDeviceById(id: string) {
  const normalized = normalizeDeviceId(id);
  return normalized ? devicesById.get(normalized) : undefined;
}

export function getDeviceBySlug(slug: string) {
  return devicesBySlug.get(slug.toLocaleLowerCase("en"));
}

export function isKnownDeviceId(id: string) {
  return getDeviceById(id) !== undefined;
}

export function compareDeviceNames(left: Device, right: Device) {
  return (
    left.manufacturer.localeCompare(right.manufacturer, "en", { sensitivity: "base" }) ||
    left.name.localeCompare(right.name, "en", { sensitivity: "base" }) ||
    left.id.localeCompare(right.id, "en")
  );
}

export function deviceSearchScore(device: Device, query: string) {
  const normalizedQuery = normalizeSearch(query);
  if (!normalizedQuery) return 0;

  const normalizedId = normalizeSearch(device.id);
  const normalizedName = normalizeSearch(device.name);
  const normalizedManufacturer = normalizeSearch(device.manufacturer);
  const normalizedAliases = device.aliases.map(normalizeSearch);
  const searchable = [
    normalizedManufacturer,
    normalizedName,
    normalizedId,
    ...normalizedAliases,
  ].join(" ");

  if (normalizedId === normalizedQuery) return 10_000;
  if (normalizedAliases.includes(normalizedQuery)) return 9_000;
  if (normalizedName === normalizedQuery) return 8_500;

  const tokens = normalizedQuery.split(" ").filter(Boolean);
  if (!tokens.every((token) => searchable.includes(token))) return null;

  let score = tokens.length * 30;
  if (searchable.includes(normalizedQuery)) score += 180;
  if (normalizedName.startsWith(normalizedQuery)) score += 220;
  if (normalizedManufacturer.startsWith(normalizedQuery)) score += 260;
  if (tokens[0] && normalizedManufacturer.startsWith(tokens[0])) score += 700;
  if (normalizedAliases.some((alias) => alias.startsWith(normalizedQuery))) score += 240;
  if (device.curated_metadata) score += 40;
  return score;
}

export function searchDevices(query: string) {
  const normalized = query.trim();
  if (!normalized) return [...devices];

  return devices
    .map((device) => ({ device, score: deviceSearchScore(device, normalized) }))
    .filter(
      (item): item is { device: Device; score: number } =>
        item.score !== null,
    )
    .sort(
      (left, right) =>
        right.score - left.score ||
        Number(right.device.curated_metadata) - Number(left.device.curated_metadata) ||
        compareDeviceNames(left.device, right.device),
    )
    .map((item) => item.device);
}
