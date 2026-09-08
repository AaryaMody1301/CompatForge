import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CompatForge | Evidence-first hardware compatibility",
    template: "%s | CompatForge",
  },
  description:
    "Check developer-hardware compatibility against explicit vendor support and configuration evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="shell header-inner">
            <Link className="brand" href="/">
              CompatForge
            </Link>
            <nav aria-label="Primary navigation">
              <Link href="/check">Check</Link>
              <Link href="/devices">Devices</Link>
              <Link href="/coverage">Coverage</Link>
              <Link href="/submissions">Contribute</Link>
              <Link href="/methodology">Methodology</Link>
            </nav>
          </div>
        </header>
        {children}
        <footer className="site-footer">
          <div className="shell footer-inner">
            <p>Evidence-first hardware compatibility. Unknown stays unknown.</p>
            <a href="https://github.com/AaryaMody1301/CompatForge">GitHub</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
