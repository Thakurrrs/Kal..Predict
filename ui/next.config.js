/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true
  },
  async rewrites() {
    const target = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8030";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/api/:path*`
      }
    ];
  }
};

module.exports = nextConfig;
