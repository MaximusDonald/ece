import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jetbrains-mono',
});

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
    <html lang="fr" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-sans antialiased bg-slate-50 text-slate-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}