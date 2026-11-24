import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep authenticated routes request-scoped. Do not cache personalized HTML.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
