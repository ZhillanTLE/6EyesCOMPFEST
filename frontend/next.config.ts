import type { NextConfig } from "next";

/**
 * The recovery API is proxied rather than called cross-origin.
 *
 * The browser talks to /api/recovery/* on its own origin and Next forwards to
 * Flask, so there is no CORS negotiation, no NEXT_PUBLIC_ backend URL baked
 * into the client bundle, and the same code path works in dev and in
 * docker compose -- only WINDFALL_API_ORIGIN changes.
 */
const apiOrigin = process.env.WINDFALL_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  /*
   * The rewrite proxy gives up after 30 seconds by default, and a pipeline run
   * is three sequential Gemini calls. On a free-tier key a single Classifier
   * call has been measured at 13-19s, so a normal run overruns that ceiling:
   * the backend completes and logs its whole trace while the browser gets a
   * plain-text 500 from the proxy, which reads to the console as "cannot reach
   * the backend" -- pointing at the one thing that is definitely fine.
   *
   * Three minutes is chosen to sit above the slowest run observed (~66s for a
   * single call) with room to spare. It bounds the wait; it does not make
   * anything asynchronous -- the request is still one synchronous cycle.
   */
  experimental: {
    proxyTimeout: 180_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/recovery/:path*",
        destination: `${apiOrigin}/api/recovery/:path*`,
      },
    ];
  },
};

export default nextConfig;
