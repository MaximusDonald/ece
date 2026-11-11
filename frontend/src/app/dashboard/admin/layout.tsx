'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useMe } from '@/hooks/useApi';
import { LoadingState } from '@/components/ui/feedback';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: currentUser, isLoading } = useMe();
  const isPlatformAdmin = currentUser?.is_superuser || currentUser?.role === 'platform_admin';

  React.useEffect(() => {
    if (!isLoading && !isPlatformAdmin) {
      router.replace('/dashboard');
    }
  }, [currentUser, isLoading, isPlatformAdmin, router]);

  if (isLoading || !isPlatformAdmin) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingState label="Vérification des droits d’administration…" />
      </div>
    );
  }

  return <div className="w-full max-w-7xl mx-auto space-y-6">{children}</div>;
}
