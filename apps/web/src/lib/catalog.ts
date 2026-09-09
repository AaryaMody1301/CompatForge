import releasePreviewDevices from "../../../../data/catalog/release-preview-devices.json";

export type Device = {
  id: string;
  slug: string;
  manufacturer: string;
  name: string;
  category: string;
  summary: string;
  identity_source: string;
};

export const devices: readonly Device[] = releasePreviewDevices;

export function getDeviceById(id: string) {
  return devices.find((device) => device.id === id);
}

export function getDeviceBySlug(slug: string) {
  return devices.find((device) => device.slug === slug);
}
