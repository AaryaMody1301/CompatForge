import publishedUsbCatalog from "../../../../data/catalog/usb-device-catalog.json";
import releasePreviewDevices from "../../../../data/catalog/release-preview-devices.json";

type PublishedCatalog = {
  counts: { devices: number; vendors: number };
  schema_version: number;
  source: {
    homepage: string;
    license: string;
    name: string;
    parser_version: string;
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
  reviewed_metadata: boolean;
};

const published = publishedUsbCatalog as unknown as PublishedCatalog;
const curated = releasePreviewDevices as readonly CuratedDevice[];
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

export function normalizeDeviceId(value: string) {
  const match = /^usb:([0-9a-f]{4}):([0-9a-f]{4})$/i.exec(value.trim());
  return match ? canonicalDeviceId(match[1], match[2]) : null;
}

const generatedDevices = published.vendors.flatMap(([vendorId, vendorName, products]) =>
  products.map(([productId, productName]) => {
    const id = canonicalDeviceId(vendorId, productId);
    const curatedDevice = curatedById.get(id);
    if (curatedDevice) {
      return { ...curatedDevice, reviewed_metadata: true } satisfies Device;
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
      reviewed_metadata: false,
    } satisfies Device;
  }),
);

export const devices: readonly Device[] = generatedDevices;
export const reviewedDevices: readonly Device[] = devices.filter(
  (device) => device.reviewed_metadata,
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
