'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useMe } from '@/hooks/useApi';
import { Shield, Loader2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const pathname = usePathname();
  const { data: user, isLoading, error } = useMe();

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        if (pathname === '/' || pathname === '/auth/login' || pathname === '/auth/register') {
          router.push('/dashboard');
        }
      } else {
        if (pathname !== '/auth/login' && pathname !== '/auth/register') {
          router.push('/auth/login');
        }
      }
    }
  }, [user, isLoading, router, pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-sovereign-100 mb-4">
            <Shield className="w-8 h-8 text-sovereign-600" />
          </div>
          <Loader2 className="h-8 w-8 animate-spin text-sovereign-500 mx-auto" />
          <p className="mt-4 text-slate-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return null;
}