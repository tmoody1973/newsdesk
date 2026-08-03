"use client";

import { useState } from "react";

/** One click, one caption on the clipboard. Silent success — the label flips
 *  to "Copied" for a moment instead of raising a toast over the text the
 *  journalist is about to paste somewhere else. */
export function CopyCaption({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-secondary"
      style={{ fontSize: 12, padding: "6px 14px" }}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        } catch {
          // Clipboard can be denied; select-and-copy still works on the <pre>.
        }
      }}
    >
      {copied ? "Copied ✓" : "Copy"}
    </button>
  );
}
