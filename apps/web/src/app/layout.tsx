import type { Metadata } from "next";
import Link from "next/link";

import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";
import { getCommunityFeatureState } from "@/lib/supabase/config";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} | Evidence-first hardware compatibility`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: `${SITE_NAME} | Evidence-first hardware compatibility`,
    description: SITE_DESCRIPTION,
    url: "/",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: SITE_NAME }],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} | Evidence-first hardware compatibility`,
    description: SITE_DESCRIPTION,
    images: ["/twitter-image"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const communityReady = getCommunityFeatureState() === "ready";

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
              {communityReady ? <Link href="/submissions">Contribute</Link> : null}
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
