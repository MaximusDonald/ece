import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Providers } from './providers';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: 'ECO-Compliance Engine (ECE) — Audit juridique souverain CEDEAO & UEMOA',
    template: '%s | ECO-Compliance Engine',
  },
  description:
    "Plateforme B2B souveraine d'audit documentaire automatisé et de vérification de conformité juridique et technique pour la zone CEDEAO, UEMOA, OHADA, OAPI et les droits nationaux.",
  keywords: [
    'conformité juridique',
    'audit automatisé',
    'CEDEAO',
    'UEMOA',
    'OHADA',
    'BCEAO',
    'Bénin',
    'protection des données',
  ],
  authors: [{ name: 'ECO-Compliance Engine Team' }],
  creator: 'ECO-Compliance Engine',
  publisher: 'ECO-Compliance Engine',
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'fr_FR',
    url: siteUrl,
    title: 'ECO-Compliance Engine — Audit juridique souverain CEDEAO & UEMOA',
    description:
      "Analysez vos contrats, politiques de confidentialité et architectures sur le corpus officiel CEDEAO, UEMOA, OHADA et national avec score stabilisé et piste d'audit.",
    siteName: 'ECO-Compliance Engine',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ECO-Compliance Engine — Audit juridique souverain',
    description:
      'Audit documentaire multi-pièces ancré sur le droit CEDEAO, UEMOA, OHADA et national.',
  },
};

export const viewport: Viewport = {
  themeColor: '#0052A5',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="font-sans antialiased bg-slate-50 text-slate-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
