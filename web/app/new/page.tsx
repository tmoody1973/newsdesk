"use client";

/**
 * The wizard. Three steps, one draft, and two calls to the worker.
 *
 * The split between the calls is not arbitrary. `Write script` runs only the
 * script stage — text, cents, no images — so the journalist sees what the model
 * wrote and what it traced BEFORE any money is spent on pictures. `Send to
 * generation` is the one that costs dollars, and it is the last thing on the
 * last step for that reason.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArtDirection } from "@/components/ArtDirection";
import { FactsAndSources } from "@/components/FactsAndSources";
import { ScriptReview } from "@/components/ScriptReview";
import { WizardSteps } from "@/components/WizardSteps";
import { Draft, emptyDraft, factsReady, slugify, toPayload } from "@/lib/draft";
import type { Block } from "@/lib/types";
import { WorkerError, lastError, startRun, waitFor } from "@/lib/worker";

export default function NewStory() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [slug, setSlug] = useState("");
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [accessCode, setAccessCode] = useState("");

  async function writeScript() {
    setProblem(null);
    setBusy("Writing the script — checking every claim against your facts…");
    const id = slugify(draft.title);
    setSlug(id);
    try {
      await startRun({
        story: toPayload(draft, id),
        stages: ["script"],
        accessCode,
      });
      const state = await waitFor(id, (s) => s.blocks.length > 0 && s.blocks.every((b) => b.narration));
      const failed = lastError(state);
      if (failed) {
        // A refused script is the product working. The model wrote a line that
        // did not trace, the validator caught it, and nothing was spent on
        // pictures — so say what happened rather than "something went wrong".
        setProblem(failed);
        return;
      }
      if (!state) {
        setProblem("The worker stopped answering. Nothing was spent on pictures.");
        return;
      }
      setBlocks(state.blocks);
      setStep(3);
    } catch (err) {
      setProblem(err instanceof WorkerError ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function sendToGeneration() {
    setProblem(null);
    setBusy("Starting the run…");
    try {
      await startRun({
        story: toPayload(draft, slug),
        // Not assembly. Publishing needs a named human, and that name is
        // collected on Editor Review after the blocks exist — never here, where
        // nobody has seen a frame yet.
        stages: ["gate", "blocks", "narration"],
        accessCode,
      });
      router.push(`/runs/${slug}`);
    } catch (err) {
      setProblem(err instanceof WorkerError ? err.message : String(err));
      setBusy(null);
    }
  }

  return (
    <main style={{ margin: "-28px -36px 0" }}>
      <WizardSteps active={step} />

      {problem && (
        <div
          style={{
            margin: "24px 36px 0",
            border: "1px solid var(--color-accent)",
            background: "var(--color-accent-100)",
            padding: 16,
          }}
        >
          <p
            className="mono"
            style={{ fontSize: 12, color: "var(--color-accent-700)", margin: 0, whiteSpace: "pre-wrap" }}
          >
            {problem}
          </p>
        </div>
      )}

      {busy && (
        <div
          style={{
            margin: "24px 36px 0",
            border: "1px solid var(--color-divider)",
            background: "var(--color-surface)",
            padding: 16,
          }}
        >
          <p className="mono" style={{ fontSize: 12, margin: 0 }}>
            {busy}
          </p>
        </div>
      )}

      <div style={{ padding: "0 36px 40px" }}>
        {step === 1 && (
          <FactsAndSources
            draft={draft}
            onChange={setDraft}
            ready={factsReady(draft)}
            onNext={() => setStep(2)}
          />
        )}

        {step === 2 && (
          <>
            <ArtDirection
              value={draft.throughLine}
              onChange={(id) => setDraft({ ...draft, throughLine: id })}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: "2px solid var(--color-divider)",
                paddingTop: 16,
                marginTop: 28,
                gap: 16,
              }}
            >
              <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setStep(1)}>
                  Back
                </button>
                <p
                  className="mono"
                  style={{ fontSize: 11, color: "var(--color-neutral-600)", margin: 0, maxWidth: 520 }}
                >
                  Requests outside this menu are checked against policy. Real people&apos;s
                  likenesses and photoreal news scenes will be blocked.
                </p>
              </div>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <input
                  className="input mono"
                  style={{ width: 180, fontSize: 12 }}
                  placeholder="access code"
                  value={accessCode}
                  onChange={(e) => setAccessCode(e.target.value)}
                  aria-label="Access code"
                />
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy !== null}
                  onClick={writeScript}
                >
                  Write script
                </button>
              </div>
            </div>
          </>
        )}

        {step === 3 && (
          <ScriptReview blocks={blocks} onSend={sendToGeneration} sending={busy !== null} />
        )}
      </div>
    </main>
  );
}
