/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    // Los PDFs se suben mediante una server action: el límite por defecto es 1 MB
    serverActions: { bodySizeLimit: "25mb" },
  },
};
export default nextConfig;
