import type { NextConfig } from "next";

// Proxy /api/* to the backend so the browser only ever talks to THIS origin,
// keeping the session cookie first-party (browsers now block third-party
// cookies, which broke cross-site Vercel↔Render auth).
//
// Locally we default to the local backend. In a deployed build we ONLY add the
// rewrite when BACKEND_ORIGIN is explicitly set to a real URL — otherwise we add
// no rewrite at all, because a rewrite pointing at localhost makes Vercel reject
// every request with DNS_HOSTNAME_RESOLVED_PRIVATE (404s the whole site).
const isDev = process.env.NODE_ENV !== "production";
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || (isDev ? "http://localhost:8000" : "");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "api.dicebear.com" },
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
    ],
  },
  async rewrites() {
    if (!BACKEND_ORIGIN) return [];   // no backend configured → no proxy (don't break routing)
    return [{ source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
