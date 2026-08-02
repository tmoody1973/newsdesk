import type { Metadata } from "next";
import { Anton, Archivo, IBM_Plex_Mono } from "next/font/google";

import "./globals.css";
import { Rail } from "@/components/Rail";

// Archivo is the design system's face and carries the chrome. Anton is for
// stamps and screen titles only — it is also the burned-subtitle face in the
// videos, which is the UI spec's continuity rule made literal. Plex Mono
// carries every piece of provenance: hashes, model ids, timestamps, fact ids.
const archivo = Archivo({ subsets: ["latin"], variable: "--font-archivo" });
const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const plexMono = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Newsdesk — governed generative video for newsrooms",
  description:
    "Verified facts in, a broadcast-style explainer out, with an editorial policy gate in front of it and a verifiable provenance receipt embedded in the file.",
  // The tab icon is the two-bar mark, not the three-bar one. Measured: at 16px
  // the full mark's inter-bar gaps fall to 0.8px and it reads as a smudge.
  icons: { icon: "/brand/favicon.svg", apple: "/brand/newsdesk-mark-light.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        className={`${archivo.variable} ${anton.variable} ${plexMono.variable}`}
        style={{ fontFamily: "var(--font-archivo), system-ui, sans-serif" }}
      >
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <Rail />
          <div style={{ flex: 1, padding: "28px 36px", minWidth: 0 }}>{children}</div>
        </div>
      </body>
    </html>
  );
}
