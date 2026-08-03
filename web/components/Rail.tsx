"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * The 64px icon rail from the mockup. Anton "N" in accent red at the top, then
 * four cells; the active one is a canary square with ink glyph.
 *
 * Canary appears in exactly two places in this product — this cell and the
 * wizard's active-step underline. It is the selection colour and nothing else.
 */
const ITEMS = [
  {
    href: "/desk",
    label: "Desk",
    icon: (
      <>
        <rect x="3" y="4" width="18" height="16" />
        <path d="M3 9h18" />
      </>
    ),
  },
  {
    href: "/brand-kit",
    label: "Brand Kit",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 3v18M3 12h18" />
      </>
    ),
  },
  {
    href: "/policy",
    label: "Policy",
    icon: <path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z" />,
  },
  {
    href: "/redteam",
    label: "Red team",
    icon: <path d="M4 6h16M4 12h16M4 18h10" />,
  },
  {
    href: "/about",
    label: "How it works",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 16v-4M12 8h.01" />
      </>
    ),
  },
];

export function Rail() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Sections"
      style={{
        width: 64,
        borderRight: "2px solid var(--color-divider)",
        background: "var(--color-surface)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "16px 0",
        gap: 6,
      }}
    >
      {/* The brand mark, replacing the Anton "N" that stood in for it. The rail
          renders it at 28px, which is inside the band where the two-bar mark
          holds and the three-bar one starts to close up. */}
      <Link href="/" aria-label="Newsdesk — front page" style={{ marginBottom: 18, lineHeight: 0 }}>
        <img src="/brand/newsdesk-mark-small-light.svg" alt="" width={28} height={28} />
      </Link>
      {ITEMS.map((item) => {
        const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link key={item.href} href={item.href} title={item.label} aria-label={item.label}>
            <span className="rail-cell" data-active={active}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {item.icon}
              </svg>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
