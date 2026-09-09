import type { Metadata } from "next";
import Link from "next/link";
import { devices } from "@/lib/catalog";
import { getDeviceEvidence } from "@/lib/evidence";

export const metadata: Metadata = { title: "Devices" };

type Props = { searchParams: Promise<{ q?: string | string[] }> };

export default async function DevicesPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q.trim() : "";
  const normalized = query.toLocaleLowerCase("en");
  const results = normalized
    ? devices.filter((device) =>
        [device.name, device.manufacturer, device.category, device.id, ...device.aliases]
          .join(" ")
          .toLocaleLowerCase("en")
          .includes(normalized),
      )
    : devices;

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Device catalog</p>
        <h1>Browse known hardware identities.</h1>
        <p>
          Identity coverage is broader than compatibility evidence. Devices without reviewed support
          or observations remain explicitly unknown.
        </p>
        <form className="search-form" action="/devices" method="get">
          <label htmlFor="device-search">Search devices</label>
          <div className="search-row">
            <input
              id="device-search"
              name="q"
              defaultValue={query}
              placeholder="FT232R, CP210x, CH340, Saleae, usb:0403:6001…"
            />
            <button type="submit">Search</button>
          </div>
        </form>
      </section>

      <section>
        <p className="meta">{results.length} result(s){query ? ` for “${query}”` : ""}</p>
        <div className="grid grid-two">
          {results.map((device) => {
            const evidence = getDeviceEvidence(device.id);
            const hasEvidence =
              evidence.supportStatements.length > 0 || evidence.observations.length > 0;
            return (
              <article className="card device-card" key={device.id}>
                <p className="kicker">{device.category}</p>
                <h2 className="card-title">{device.manufacturer} {device.name}</h2>
                <code>{device.id}</code>
                <p>{device.summary}</p>
                <p className="meta">
                  {hasEvidence
                    ? `${evidence.supportStatements.length} support · ${evidence.observations.length} observed`
                    : "Identity known · compatibility evidence unknown"}
                </p>
                <div className="card-actions">
                  <Link href={`/devices/${device.slug}`}>
                    {hasEvidence ? "Review evidence" : "Identity details"}
                  </Link>
                  <Link href={`/check?device=${encodeURIComponent(device.id)}`}>Check configuration</Link>
                </div>
              </article>
            );
          })}
        </div>
        {results.length === 0 ? (
          <div className="empty-state">
            <h2>No catalog identity matches that search.</h2>
            <p>Try a product name, vendor, alias, or canonical USB VID/PID.</p>
          </div>
        ) : null}
      </section>
    </main>
  );
}
