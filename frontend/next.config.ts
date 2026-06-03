import type { NextConfig } from "next";
import path from "path";

const frontendRoot = path.resolve(__dirname);

const nextConfig: NextConfig = {
  ...(process.env.NODE_ENV === "production"
    ? { output: "standalone" as const, outputFileTracingRoot: frontendRoot }
    : {}),
  turbopack: {
    root: frontendRoot,
  },
  async redirects() {
    return [
      { source: "/landing", destination: "/landing/index.html", permanent: false },
      { source: "/landing/", destination: "/landing/index.html", permanent: false },
    ];
  },
};

export default nextConfig;
