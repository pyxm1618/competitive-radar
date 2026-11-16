/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow an isolated build dir (e.g. for verifying a prod build while a dev
  // server keeps using .next). Defaults to .next.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
