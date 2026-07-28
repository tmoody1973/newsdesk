import { GetObjectCommand, ListObjectsV2Command, S3Client } from "@aws-sdk/client-s3";

import type { RunState } from "./types";

/**
 * B2 reads, server-side only.
 *
 * `newsdesk-runs` and `newsdesk-manifests` are PRIVATE, so these credentials
 * live in the server component and never reach the browser. `newsdesk-assets`
 * and `newsdesk-brand-kit` are public on purpose — the receipt tells a
 * fact-checker to verify the MP4 themselves, and a verification that required
 * our permission would not be one.
 */

const REGION = (process.env.B2_REGION ?? "").match(/([a-z]{2}-[a-z]+-\d{3})/)?.[1];

export const BUCKETS = {
  assets: process.env.B2_BUCKET_ASSETS ?? "newsdesk-assets",
  brandKit: process.env.B2_BUCKET_BRAND_KIT ?? "newsdesk-brand-kit",
  manifests: process.env.B2_BUCKET_MANIFESTS ?? "newsdesk-manifests",
  runs: process.env.B2_BUCKET_RUNS ?? "newsdesk-runs",
};

let cached: S3Client | null = null;

function client(): S3Client {
  if (!REGION) throw new Error("B2_REGION is not set — see api/.env.example");
  if (!cached) {
    cached = new S3Client({
      region: REGION,
      endpoint: `https://s3.${REGION}.backblazeb2.com`,
      credentials: {
        accessKeyId: process.env.B2_KEY_ID ?? "",
        secretAccessKey: process.env.B2_APP_KEY ?? "",
      },
    });
  }
  return cached;
}

export function publicUrl(bucket: string, key: string): string {
  return `https://s3.${REGION}.backblazeb2.com/${bucket}/${key}`;
}

async function text(bucket: string, key: string): Promise<string | null> {
  try {
    const out = await client().send(new GetObjectCommand({ Bucket: bucket, Key: key }));
    return (await out.Body?.transformToString()) ?? null;
  } catch {
    return null;
  }
}

async function keys(bucket: string, prefix: string): Promise<string[]> {
  const found: string[] = [];
  let token: string | undefined;
  do {
    const page = await client().send(
      new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix, ContinuationToken: token }),
    );
    for (const o of page.Contents ?? []) if (o.Key) found.push(o.Key);
    token = page.NextContinuationToken;
  } while (token);
  return found;
}

/** Every run on the board. One state.json per run — there is no database. */
export async function listRuns(): Promise<RunState[]> {
  const found = await keys(BUCKETS.runs, "");
  const states = await Promise.all(
    found.filter((k) => k.endsWith("/state.json")).map((k) => text(BUCKETS.runs, k)),
  );
  return states
    .filter((s): s is string => Boolean(s))
    .map((s) => JSON.parse(s) as RunState)
    .sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
}

export async function getRun(runId: string): Promise<RunState | null> {
  const raw = await text(BUCKETS.runs, `${runId}/state.json`);
  return raw ? (JSON.parse(raw) as RunState) : null;
}

export async function brandKitFile(name: string): Promise<string | null> {
  return text(BUCKETS.brandKit, `kit/${name}`);
}

/** The finished film, if this run produced one. */
export async function finalVideo(runId: string): Promise<string | null> {
  const found = await keys(BUCKETS.assets, `${runId}/`);
  const mp4 = found.find((k) => k.endsWith(".mp4"));
  return mp4 ? publicUrl(BUCKETS.assets, mp4) : null;
}
