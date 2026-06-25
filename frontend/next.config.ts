import type { NextConfig } from "next";

// Proxy /api/* to the backend so the browser only ever talks to THIS origin.
// That keeps the session cookie first-party — required because browsers
// (Safari + Chrome) now block third-party cookies, which broke cross-site
// auth (Vercel frontend ↔ Render backend). Set BACKEND_ORIGIN in the deploy
// env (e.g. https://pm-agent-api-84i4.onrender.com); defaults to local dev.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "api.dicebear.com" },
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
    ],
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
