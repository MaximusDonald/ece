import type { MetadataRoute } from 'next';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/privacy', '/terms', '/auth/login', '/auth/register'],
        disallow: ['/dashboard/', '/api/', '/auth/forgot-password'],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
