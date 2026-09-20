import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: process.cwd(),
  skipTrailingSlashRedirect: true,
  experimental: {
    // Multipart overhead must fit as well as the backend's 200 MiB file limit.
    middlewareClientMaxBodySize: "201mb",
    proxyTimeout: 120000,
  },
  async rewrites() {
    const backendUrl = process.env.INTERNAL_BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

