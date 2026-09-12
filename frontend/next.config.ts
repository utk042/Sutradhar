import createNextIntlPlugin from 'next-intl/plugin';
import type {NextConfig} from 'next';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

/**
 * The backend origin. Server-side only — never shipped to the browser, because
 * the browser always talks to this app's own origin (see the rewrite below).
 */
const API_ORIGIN = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  /**
   * Proxy the API through this origin.
   *
   * The session cookie is SameSite=Strict, and a browser does not send a Strict
   * cookie on a cross-site request. With the frontend on :3000 and FastAPI on
   * :8000 the browser treats every API call as cross-site, so sign-in would set
   * the cookie and the very next request would arrive without it.
   *
   * Proxying means the browser only ever sees one origin: Strict does what it is
   * meant to do, and CORS stops being involved at all.
   */
  async rewrites() {
    return [{source: '/api/:path*', destination: `${API_ORIGIN}/api/:path*`}];
  },
  // The UX4G stylesheet is ~8 MB because the package embeds seven fonts as
  // base64. Serving it from our own origin with an immutable cache header
  // makes it a once-per-release cost per browser rather than a per-visit one.
  // See README, "Known constraint: stylesheet size".
  async headers() {
    return [
      {
        source: '/_next/static/:path*',
        headers: [{key: 'Cache-Control', value: 'public, max-age=31536000, immutable'}]
      }
    ];
  }
};

export default withNextIntl(nextConfig);
