/** @type {import('next').NextConfig} */
export default {
  // The run state and manifests live in a PRIVATE bucket, so every read happens
  // in a server component with credentials that never reach the browser.
  experimental: { serverActions: { bodySizeLimit: "2mb" } },
  // policy.yaml lives at the repo root and is read at request time. Traced in
  // rather than copied, so there is exactly one policy file and the page cannot
  // drift from the one the gate enforces.
  outputFileTracingRoot: new URL("..", import.meta.url).pathname,
  outputFileTracingIncludes: { "/policy": ["../policy/policy.yaml"] },
};
