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
