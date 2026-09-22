import type { Metadata } from "next";

export const SITE_NAME = "CompatForge";
export const SITE_URL = "https://compat-forge.vercel.app";
export const SITE_DESCRIPTION =
  "Evidence-first developer hardware compatibility: USB identity, vendor support, and observed results kept separate.";

export function pageMetadata(
  title: string,
  description: string,
  path: string,
): Metadata {
  const fullTitle = `${title} | ${SITE_NAME}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      title: fullTitle,
      description,
      url: path,
      images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: SITE_NAME }],
    },
    twitter: {
      card: "summary_large_image",
      title: fullTitle,
      description,
      images: ["/twitter-image"],
    },
  };
}

export function countLabel(
  count: number,
  singular: string,
  plural = `${singular}s`,
) {
  return `${count.toLocaleString("en")} ${count === 1 ? singular : plural}`;
}
