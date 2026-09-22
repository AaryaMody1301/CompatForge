import { ImageResponse } from "next/og";

export const alt = "CompatForge — evidence-first hardware compatibility";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function SocialImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#080b10",
          color: "#f3f6fa",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ fontSize: 34, fontWeight: 800, color: "#8cd3ff" }}>CompatForge</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 72, fontWeight: 800, lineHeight: 1.02, maxWidth: 980 }}>
            Evidence-first hardware compatibility.
          </div>
          <div style={{ fontSize: 30, color: "#aab5c4", maxWidth: 980 }}>
            USB identity, vendor support, and observed results stay separate. Unknown stays unknown.
          </div>
        </div>
      </div>
    ),
    size,
  );
}
