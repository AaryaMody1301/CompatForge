import type { Metadata } from "next";
import Link from "next/link";

import { catalogCounts, devices } from "@/lib/catalog";
import { getDeviceEvidence } from "@/lib/evidence";

export const metadata: Metadata = { title: "Devices" };

const PAGE_SIZE = 48;

type Props = {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
};

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function pageHref(query: string, page: number) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (page > 1) params.set("page", String(page));
  const suffix = params.toString();
  return suffix ? `/devices?${suffix}` : "/devices";
}

export default async function DevicesPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = (first(params.q) ?? "").trim();
  const normalized = query.toLocaleLowerCase("en");
  const parsedPage = Number.parseInt(first(params.page) ?? "1", 10);

  const results = normalized
    ? devices.filter((device) =>
        [device.name, device.manufacturer, device.category, device.id, ...device.aliases]
          .join(" ")
          .toLocaleLowerCase("en")
          .includes(normalized),
      )
    : devices;

  const pageCount = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const currentPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? Math.min(parsedPage, pageCount) : 1;
  const offset = (currentPage - 1) * PAGE_SIZE;
  const visibleDevices = results.slice(offset, offset + PAGE_SIZE);
  const rangeStart = results.length ? offset + 1 : 0;
  const rangeEnd = Math.min(offset + PAGE_SIZE, results.length);

  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Device catalog</p>
        <h1>Browse known hardware identities.</h1>
        <p>
          The catalog publishes the full reviewed USB identity snapshot. Identity coverage is broader
          than compatibility evidence, so devices without reviewed support or observations remain
          explicitly unknown.
        </p>
        <form className="search-form" action="/devices" method="get">
          <label htmlFor="device-search">Search devices</label>
          <div className="search-row">
            <input
              id="device-search"
              name="q"
              defaultValue={query}
              placeholder="FT232R, Arduino, Logitech, usb:0403:6001…"
            />
            <button type="submit">Search</button>
          </div>
        </form>
      </section>

      <section>
        <p className="meta">
          Showing {rangeStart}–{rangeEnd} of {results.length.toLocaleString("en")} result(s)
          {query ? ` for “${query}”` : ""} · {catalogCounts.devices.toLocaleString("en")} total identities
        </p>
        <div className="grid grid-two">
          {visibleDevices.map((device) => {
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

        {pageCount > 1 ? (
          <nav className="pagination" aria-label="Device catalog pages">
            {currentPage > 1 ? (
              <Link className="button" href={pageHref(query, currentPage - 1)}>Previous</Link>
            ) : (
              <span className="button button-disabled" aria-disabled="true">Previous</span>
            )}
            <span className="meta">Page {currentPage.toLocaleString("en")} of {pageCount.toLocaleString("en")}</span>
            {currentPage < pageCount ? (
              <Link className="button" href={pageHref(query, currentPage + 1)}>Next</Link>
            ) : (
              <span className="button button-disabled" aria-disabled="true">Next</span>
            )}
          </nav>
        ) : null}
      </section>
    </main>
  );
}
