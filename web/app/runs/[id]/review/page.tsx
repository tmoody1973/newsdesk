import { notFound } from "next/navigation";

import { EditorReview } from "@/components/EditorReview";
import { getRun } from "@/lib/b2";

/** Wall 3's screen. Server-fetched, client-interactive — the run's state comes
 *  from B2, the approval gesture goes to the worker. */
export const dynamic = "force-dynamic";

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await getRun(id);
  if (!run) notFound();
  return <EditorReview run={run} />;
}
