import type { Metadata } from "next";

export const metadata: Metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <main className="shell page-stack">
      <section className="compact-hero">
        <p className="eyebrow">Methodology</p>
        <h1>Evidence first. Inference second.</h1>
        <p>
          CompatForge keeps hardware identity, vendor support, observed compatibility, and derived
          claims as separate layers so one cannot silently impersonate another.
        </p>
      </section>

      <section className="prose">
        <h2>1. Vendor support is not an observation.</h2>
        <p>
          A support statement records what a vendor documents for an operating system, architecture,
          driver, software release, or USB requirement. It can return supported without creating a
          works observation.
        </p>

        <h2>2. Observations stay configuration-specific.</h2>
        <p>
          An observation records a host, OS, architecture, connection path, result, source, and date.
          Missing topology stays unspecified. CompatForge does not infer “direct port” when a source
          only says that a USB device worked.
        </p>

        <h2>3. Relaxation is explicit.</h2>
        <p>
          The checker first looks for an exact observation, then may relax host identity, then OS
          version. It never relaxes CPU architecture, OS family, or connection path. Every relaxed
          match is labeled.
        </p>

        <h2>4. Conflicts remain visible.</h2>
        <p>
          If equally specific evidence contains both successful and failing outcomes, the claim is
          conflicting. Evidence is not averaged into an opaque probability.
        </p>

        <h2>5. Unknown is a valid answer.</h2>
        <p>
          When no applicable observation or support statement exists, the result remains unknown.
          Related evidence can still be shown without being promoted into a claim.
        </p>
      </section>
    </main>
  );
}
