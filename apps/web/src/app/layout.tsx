import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CompatForge | Evidence-first hardware compatibility",
  description:
    "Compatibility intelligence for developer hardware, grounded in explicit configuration evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
