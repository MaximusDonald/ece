'use client';

import * as React from 'react';
import { ToastProvider, ToastViewport, Toaster } from '@/components/ui/toast';
import { QueryProvider } from '@/lib/query-provider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { CookieConsentBanner } from '@/components/CookieConsentBanner';
import { AnalyticsProvider } from '@/components/AnalyticsProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <TooltipProvider>
        <ToastProvider>
          {children}
          <CookieConsentBanner />
          <AnalyticsProvider />
          <Toaster />
          <ToastViewport />
        </ToastProvider>
      </TooltipProvider>
    </QueryProvider>
  );
}
