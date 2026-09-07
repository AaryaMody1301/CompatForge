const evidenceStates = [
  ["WORKS", "Evidence supports the tested configuration."],
  ["CONDITIONAL", "Evidence supports it only under documented conditions."],
  ["FAILS", "Evidence supports an incompatibility for the tested configuration."],
  ["CONFLICTING", "Credible observations disagree and remain visible."],
  ["UNKNOWN", "There is not enough evidence to make a compatibility claim."],
] as const;

export default function Home() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Phase 1 / Evidence contracts</p>
        <h1>Hardware compatibility without guesswork.</h1>
        <p className="lede">
          CompatForge is building a vendor-independent compatibility graph for developer hardware.
          Every future result will identify the exact host, OS, architecture, connection path, driver,
          and evidence behind the claim.
        </p>
        <div className="status" role="status">
          <strong>Current release state:</strong> foundation only. No real compatibility claims are
          published yet.
        </div>
      </section>

      <section aria-labelledby="principle-title">
        <p className="eyebrow">Core rule</p>
        <h2 id="principle-title">Unknown is better than invented certainty.</h2>
        <p>
          CompatForge separates source observations from derived compatibility claims. Missing data is
          reported as unknown, while conflicts stay inspectable instead of being averaged into a score.
        </p>
      </section>

      <section aria-labelledby="states-title">
        <p className="eyebrow">Result vocabulary</p>
        <h2 id="states-title">Five states, each with evidence.</h2>
        <div className="grid">
          {evidenceStates.map(([title, description]) => (
            <article className="card" key={title}>
              <h3>{title}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="scope-title">
        <p className="eyebrow">Initial scope</p>
        <h2 id="scope-title">Start narrow. Prove the data model.</h2>
        <p>
          The first data release targets USB serial adapters, development boards,
          debuggers/programmers, and logic analyzers across Windows 11, macOS, and Ubuntu on x86-64
          and ARM64.
        </p>
      </section>
    </main>
  );
}
