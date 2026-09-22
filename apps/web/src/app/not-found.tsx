import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page not found",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Not found</p>
        <h1>That page does not exist.</h1>
        <p>The requested CompatForge route or USB identity could not be found.</p>
        <Link className="button button-primary" href="/devices">Browse devices</Link>
      </section>
    </main>
  );
}
