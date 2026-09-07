export type Device = {
  id: string;
  slug: string;
  manufacturer: string;
  name: string;
  category: string;
  summary: string;
};

export const devices: readonly Device[] = [
  {
    id: "usb:0403:6001",
    slug: "ftdi-ft232r",
    manufacturer: "FTDI",
    name: "FT232R",
    category: "USB serial adapter",
    summary: "A widely used USB-to-UART bridge in embedded development and programming workflows.",
  },
  {
    id: "usb:21A9:1005",
    slug: "saleae-logic-pro-8",
    manufacturer: "Saleae",
    name: "Logic Pro 8",
    category: "Logic analyzer",
    summary: "An eight-channel USB logic analyzer whose full capture performance depends on the host USB path.",
  },
];

export function getDeviceById(id: string) {
  return devices.find((device) => device.id === id);
}

export function getDeviceBySlug(slug: string) {
  return devices.find((device) => device.slug === slug);
}
