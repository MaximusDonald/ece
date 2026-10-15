import type { Metadata, Viewport } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'ECO-Compliance Engine (ECE)',
  description: 'Plateforme souveraine d\'audit documentaire automatisé et de vérification de conformité juridique pour la CEDEAO/UEMOA',
  keywords: ['compliance', 'audit', 'juridique', 'CEDEAO', 'UEMOA', 'Bénin', 'RGPD', 'protection données'],
  authors: [{ name: 'ECE Team' }],
  creator: 'ECE Team',
  publisher: 'ECE',
  robots: 'index, follow',
  openGraph: {
    type: 'website',
    locale: 'fr_FR',
    url: 'https://ece.example.com',
    title: 'ECO-Compliance Engine',
    description: 'Plateforme souveraine d\'audit documentaire automatisé',
    siteName: 'ECE',
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
