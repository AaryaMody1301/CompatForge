import Link from "next/link";
import { devices } from "@/lib/catalog";
import { getDeviceEvidence, observations, supportStatements } from "@/lib/evidence";

export default function Home() {
  return (
    <main className="shell page-stack">
      <section className="hero">
        <p className="eyebrow">Evidence-first compatibility</p>
        <h1>Will this hardware actually work?</h1>
        <p className="lede">
          CompatForge separates vendor support from observed compatibility, preserves conflicts, and
          returns unknown when the evidence does not justify a stronger answer.
        </p>
        <div className="actions">
          <Link className="button button-primary" href="/check">
            Check a configuration
          </Link>
          <Link className="button" href="/devices">
            Browse devices
          </Link>
        </div>
        <div className="metrics" aria-label="Current evidence corpus">
          <div>
            <strong>{devices.length}</strong>
            <span>devices</span>
          </div>
          <div>
            <strong>{supportStatements.length}</strong>
            <span>support statements</span>
          </div>
          <div>
            <strong>{observations.length}</strong>
            <span>observations</span>
          </div>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Current catalog</p>
            <h2>Small corpus, explicit evidence.</h2>
          </div>
          <Link href="/coverage">View coverage</Link>
        </div>
        <div className="grid grid-two">
          {devices.map((device) => {
            const evidence = getDeviceEvidence(device.id);
            return (
              <article className="card device-card" key={device.id}>
                <p className="kicker">{device.category}</p>
                <h3>{device.manufacturer} {device.name}</h3>
                <p>{device.summary}</p>
                <p className="meta">
                  {evidence.supportStatements.length} support statement(s) · {evidence.observations.length} observation(s)
                </p>
                <Link href={`/devices/${device.slug}`}>Inspect evidence →</Link>
              </article>
            );
          })}
        </div>
      </section>

      <section>
        <p className="eyebrow">How answers work</p>
        <h2>Two answers are better than one misleading flag.</h2>
        <div className="grid grid-three">
          <article className="card">
            <h3>Observed compatibility</h3>
            <p>What happened on a reported or reproduced configuration.</p>
          </article>
          <article className="card">
            <h3>Vendor support</h3>
            <p>What the manufacturer documents for an OS, architecture, driver, or connection class.</p>
          </article>
          <article className="card">
            <h3>Unknown</h3>
            <p>No matching evidence means no invented recommendation. Related evidence remains visible.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
