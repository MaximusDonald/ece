'use client';

import * as React from 'react';
import { ToastProvider, ToastViewport, Toaster } from '@/components/ui/toast';
import { QueryProvider } from '@/lib/query-provider';
import { TooltipProvider } from '@/components/ui/tooltip';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <TooltipProvider>
        <ToastProvider>
          {children}
          <Toaster />
          <ToastViewport />
        </ToastProvider>
      </TooltipProvider>
    </QueryProvider>
  );
}
