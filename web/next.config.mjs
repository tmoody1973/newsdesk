/** @type {import('next').NextConfig} */
export default {
  // The run state and manifests live in a PRIVATE bucket, so every read happens
  // in a server component with credentials that never reach the browser.
  experimental: { serverActions: { bodySizeLimit: "2mb" } },
  // policy.yaml lives at the repo root and is read at request time. Traced in
  // rather than copied, so there is exactly one policy file and the page cannot
  // drift from the one the gate enforces.
  outputFileTracingRoot: new URL("..", import.meta.url).pathname,
  // Every route that reads it needs its own entry — tracing is per-route, so a
  // new page reading the same file 500s in production while working locally.
  outputFileTracingIncludes: {
    "/policy": ["../policy/policy.yaml"],
    "/brand-kit": ["../policy/policy.yaml"],
  },
};
