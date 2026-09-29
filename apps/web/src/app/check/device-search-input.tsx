"use client";

import { useEffect, useId, useState } from "react";

export function DeviceSearchInput({ name, initialValue }: { name: string; initialValue: string }) {
  const [query, setQuery] = useState(initialValue);
  const [devices, setDevices] = useState<{ id: string; name: string }[]>([]);
  const listId = useId();

  useEffect(() => {
    if (query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/devices/search?q=${encodeURIComponent(query)}`, {
          signal: controller.signal,
        });
        if (response.ok) {
          const result = await response.json() as { devices: { id: string; name: string }[] };
          setDevices(result.devices);
        }
      } catch {
        // The plain text field remains usable without suggestions or network access.
      }
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query]);

  return (
    <>
      <input
        name={name}
        defaultValue={initialValue}
        onChange={(event) => {
          setQuery(event.target.value);
          if (event.target.value.trim().length < 2) setDevices([]);
        }}
        list={listId}
        required
        maxLength={80}
        pattern="usb:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}"
        placeholder="usb:0403:6001"
        autoComplete="off"
      />
      <datalist id={listId}>
        {devices.map((device) => <option key={device.id} value={device.id} label={device.name} />)}
      </datalist>
    </>
  );
}
