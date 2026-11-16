'use client';

import { useEffect, useState } from 'react';
import Script from 'next/script';
import Cookies from 'js-cookie';
import { CONSENT_COOKIE_NAME } from './CookieConsentBanner';

const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN || '';
const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || '';

export function AnalyticsProvider() {
  const [consented, setConsented] = useState(false);

  useEffect(() => {
    setConsented(Cookies.get(CONSENT_COOKIE_NAME) === 'all');
    const handler = (ev: Event) => {
      const custom = ev as CustomEvent<string>;
      setConsented(custom.detail === 'all');
    };
    window.addEventListener('ece:consent-updated', handler);
    return () => window.removeEventListener('ece:consent-updated', handler);
  }, []);

  if (!consented) return null;

  return (
    <>
      {PLAUSIBLE_DOMAIN ? (
        <Script
          defer
          data-domain={PLAUSIBLE_DOMAIN}
          src="https://plausible.io/js/script.js"
          strategy="afterInteractive"
        />
      ) : null}
      {GA_ID ? (
        <>
          <Script
            src={`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_ID)}`}
            strategy="afterInteractive"
          />
          <Script id="ece-ga-init" strategy="afterInteractive">
            {`window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);} gtag('js', new Date()); gtag('config', '${GA_ID}', { anonymize_ip: true });`}
          </Script>
        </>
      ) : null}
    </>
  );
}
