import Link from "next/link";

export default function NotFound() {
  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Not found</p>
        <h1>That evidence page does not exist.</h1>
        <p>The public catalog only exposes reviewed devices and evidence.</p>
        <Link className="button button-primary" href="/devices">Browse devices</Link>
      </section>
    </main>
  );
}
