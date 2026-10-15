'use client';

import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function LoadingState({ label = 'Chargement…' }: { label?: string }) {
  return (
    <div className="flex min-h-32 flex-col items-center justify-center gap-3 py-8 text-slate-500" role="status" aria-live="polite">
      <Loader2 className="h-7 w-7 animate-spin text-sovereign-500" aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-danger-200 bg-danger-50 px-5 py-8 text-center" role="alert">
      <AlertCircle className="h-7 w-7 text-danger-600" aria-hidden="true" />
      <p className="max-w-xl text-sm text-danger-800">{message}</p>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Réessayer
        </Button>
      )}
    </div>
  );
}
