'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Cookies from 'js-cookie';
import { Button } from '@/components/ui/button';

export const CONSENT_COOKIE_NAME = 'ece_cookie_consent';

export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const existing = Cookies.get(CONSENT_COOKIE_NAME);
    if (!existing) {
      setVisible(true);
    }
  }, []);

  const saveChoice = (value: 'essential' | 'all') => {
    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
    Cookies.set(CONSENT_COOKIE_NAME, value, {
      expires: 180,
      sameSite: 'lax',
      secure: isHttps,
      path: '/',
    });
    setVisible(false);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('ece:consent-updated', { detail: value }));
    }
  };

  if (!visible) return null;

  return (
    <aside
      role="dialog"
      aria-label="Gestion des cookies"
      className="fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-4 sm:p-5 shadow-lg"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-xs sm:text-sm text-slate-700 leading-relaxed">
          <p className="font-semibold text-slate-900 mb-1">Respect de votre vie privée</p>
          <p>
            ECE utilise des cookies strictement nécessaires à votre session et, avec votre accord, des mesures d&apos;audience anonymisées. Consultez notre{' '}
            <Link href="/privacy" className="font-medium text-sovereign-600 hover:underline">
              politique de confidentialité
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-shrink-0 flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => saveChoice('essential')}>
            Essentiels uniquement
          </Button>
          <Button size="sm" onClick={() => saveChoice('all')}>
            Tout accepter
          </Button>
        </div>
      </div>
    </aside>
  );
}
