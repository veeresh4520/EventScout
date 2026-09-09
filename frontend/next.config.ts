import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "secure.meetupstatic.com",
      },
    ],
  },
};

export default nextConfig;
