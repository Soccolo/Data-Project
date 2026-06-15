/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Images may come from Supabase storage signed URLs — allow them
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '*.supabase.co', pathname: '/storage/v1/object/**' },
    ],
  },
};
export default nextConfig;
