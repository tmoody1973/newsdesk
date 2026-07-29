"use client";

/**
 * Keeps the Run Board honest while a run is in flight.
 *
 * `router.refresh()` rather than a second data path: the page already reads
 * `state.json` from B2 on the server, and adding a client-side fetch of the
 * same document would give the screen two ways to disagree with itself.
 *
 * It stops on its own. A board that polls a finished run forever is a tab that
 * quietly costs somebody battery for an hour — and, less obviously, a run that
 * died would otherwise be indistinguishable from one still working. `done` is
 * computed by the server component from the run's own status, so "stopped
 * polling" and "stopped running" are the same fact.
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// Slower than it feels like it should be, on purpose: a stage takes tens of
// seconds to minutes, so a 1s poll would re-render the same board sixty times
// to catch one change.
const EVERY_MS = 4000;

export function LivePoll({ done, label }: { done: boolean; label?: string }) {
  const router = useRouter();
  const [ticks, setTicks] = useState(0);

  useEffect(() => {
    if (done) return;
    const id = setInterval(() => {
      setTicks((t) => t + 1);
      router.refresh();
    }, EVERY_MS);
    return () => clearInterval(id);
  }, [done, router]);

  if (done) return null;

  return (
    <span className="mono text-xs text-graphite" aria-live="polite">
      ● live{label ? ` · ${label}` : ""}
      {ticks > 0 ? ` · refreshed ${ticks}×` : ""}
    </span>
  );
}
