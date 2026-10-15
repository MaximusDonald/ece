'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useApi';
import { LoadingState } from '@/components/ui/feedback';
import {
  LayoutDashboard,
  FileText,
  Users,
  Shield,
  Database,
  Code,
  Globe,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Scale,
} from 'lucide-react';

const adminNavigation = [
  { name: 'Sources juridiques', href: '/dashboard/admin/sources', icon: Database },
  { name: 'Règles de scoring', href: '/dashboard/admin/rules', icon: Shield },
  { name: 'Modèles LLM', href: '/dashboard/admin/models', icon: Code },
  { name: 'Pays / Juridictions', href: '/dashboard/admin/countries', icon: Globe },
  { name: 'Utilisateurs', href: '/dashboard/admin/users', icon: Users },
  { name: 'Journaux d\'audit', href: '/dashboard/admin/audit', icon: FileText },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: currentUser, isLoading } = useMe();
  const logout = useLogout();
  const [collapsed, setCollapsed] = React.useState(false);

  React.useEffect(() => {
    if (!isLoading && currentUser?.role !== 'platform_admin') router.replace('/dashboard');
  }, [currentUser, isLoading, router]);

  if (isLoading || currentUser?.role !== 'platform_admin') {
    return <LoadingState label="Vérification des droits d’administration…" />;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r border-slate-200 bg-white transition-all duration-300',
          collapsed ? 'w-20' : 'w-72'
        )}
      >
        {/* Logo */}
        <div className={cn('flex items-center justify-between h-16 px-4 border-b border-slate-200', collapsed && 'justify-center')}>
          {!collapsed && (
            <Link href="/dashboard/admin/sources" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-sovereign-500 flex items-center justify-center">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-slate-900 text-lg">ECE Admin</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className={cn(collapsed && 'ml-auto')}
            aria-label={collapsed ? 'Étendre la barre latérale' : 'Réduire la barre latérale'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Navigation administration">
          {!collapsed && (
            <>
              <h3 className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Gouvernance
              </h3>
              {adminNavigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-sovereign-50 text-sovereign-600'
                        : 'text-slate-600 hover:bg-sovereign-50 hover:text-sovereign-600'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </>
          )}

          {collapsed && (
            <>
              {adminNavigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center justify-center px-3 py-2.5 rounded-lg transition-colors mx-2',
                      isActive
                        ? 'bg-sovereign-50 text-sovereign-600'
                        : 'text-slate-600 hover:bg-sovereign-50 hover:text-sovereign-600'
                      )
                    }
                    aria-current={isActive ? 'page' : undefined}
                    title={item.name}
                  >
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* Back to app */}
        <div className={cn('p-4 border-t border-slate-200', collapsed && 'hidden')}>
          <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-sovereign-50 hover:text-sovereign-600 transition-colors">
            <LayoutDashboard className="h-5 w-5" />
            <span>Retour à l'application</span>
          </Link>
          <Button variant="ghost" className="w-full justify-start mt-2" onClick={() => {
            logout.mutate(undefined, { onSettled: () => router.replace('/auth/login') });
          }} disabled={logout.isPending}>
            <LogOut className="h-4 w-4 mr-2" />
            Déconnexion
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main
        className={cn(
          'min-h-screen transition-all duration-300',
          collapsed ? 'ml-20' : 'ml-72'
        )}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-white/80 backdrop-blur-sm border-b border-slate-200">
          <div className="h-full px-6 flex items-center justify-between">
            <h1 className="text-xl font-semibold text-slate-900">
              {(() => {
                const segments = pathname.split('/').filter(Boolean);
                if (segments.length <= 2) return 'Administration';
                const last = segments[segments.length - 1];
                if (last === 'new') return 'Nouveau';
                return last.charAt(0).toUpperCase() + last.slice(1);
              })()}
            </h1>
          </div>
        </header>

        {/* Page content */}
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}

export default AdminLayout;
