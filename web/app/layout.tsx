import type { Metadata } from "next";
import { Anton, IBM_Plex_Mono, Public_Sans } from "next/font/google";
import Link from "next/link";

import "./globals.css";

// Anton is already the burned-subtitle face in the videos. Using it for stamps
// and display means the tool and the media it produces are visibly the same
// product — the UI spec's continuity rule, made literal.
const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-public-sans" });
const plexMono = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "Newsdesk — governed generative video for newsrooms",
  description:
    "Verified facts in, a broadcast-style explainer out, with an editorial policy gate in front of it and a verifiable provenance receipt embedded in the file.",
};

const RAIL = [
  { href: "/", label: "Desk" },
  { href: "/policy", label: "Policy" },
  { href: "/redteam", label: "Red team" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${anton.variable} ${publicSans.variable} ${plexMono.variable}`}>
        <div className="mx-auto max-w-6xl px-5 py-6">
          <header className="mb-8 flex flex-wrap items-baseline justify-between gap-4 border-b-2 border-ink pb-3">
            <Link href="/" className="font-display text-2xl uppercase tracking-wide">
              Newsdesk
            </Link>
            <nav className="flex gap-5 text-sm">
              {RAIL.map((item) => (
                <Link key={item.href} href={item.href} className="hover:text-approval-blue">
                  {item.label}
                </Link>
              ))}
              <a
                href="https://github.com/tmoody1973/newsdesk"
                className="text-graphite hover:text-approval-blue"
              >
                Source
              </a>
            </nav>
          </header>
          {children}
          <footer className="mono mt-16 border-t border-graphite/40 pt-4 text-xs text-graphite">
            Its most important feature is what it refuses to make.
          </footer>
        </div>
      </body>
    </html>
  );
}
