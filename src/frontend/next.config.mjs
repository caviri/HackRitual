/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — Next produces /out which FastAPI serves at /
  output: 'export',
  trailingSlash: true,
  images: { unoptimized: true },
  experimental: {
    // Keeps app router happy with static export
  },
};

export default nextConfig;
