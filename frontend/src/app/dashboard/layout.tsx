'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useApi';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  Users,
  Settings,
  Shield,
  Database,
  Code,
  Globe,
  History,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Scale,
  Menu,
  X,
} from 'lucide-react';

const navigation = [
  { name: 'Tableau de bord', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Projets', href: '/dashboard/projects', icon: FileText },
  { name: 'Codes & Articles', href: '/dashboard/corpus', icon: Scale },
  { name: 'Équipe', href: '/dashboard/team', icon: Users },
  { name: 'Paramètres', href: '/dashboard/settings', icon: Settings },
];

const adminNavigation = [
  { name: 'Bibliothèque des Codes', href: '/dashboard/admin/corpus', icon: Scale },
  { name: 'Sentinelle réglementaire', href: '/dashboard/admin/sources', icon: Globe },
  { name: 'Archives Crawler (Legacy)', href: '/dashboard/admin/sources/documents', icon: FileText },
  { name: 'Règles de scoring', href: '/dashboard/admin/rules', icon: Shield },
  { name: 'Modèles LLM', href: '/dashboard/admin/models', icon: Code },
  { name: 'Pays / Juridictions', href: '/dashboard/admin/countries', icon: Database },
  { name: 'Utilisateurs', href: '/dashboard/admin/users', icon: Users },
  { name: 'Journaux d\'audit', href: '/dashboard/admin/audit', icon: History },
  { name: 'Paramètres système', href: '/dashboard/admin/settings', icon: Settings },
];

const getPageHeaderInfo = (pathname: string) => {
  if (pathname === '/dashboard') return { title: 'Tableau de bord', category: 'Vue générale' };
  if (pathname.includes('/upload')) return { title: 'Téléverser un document', category: 'Documents' };
  if (pathname.includes('/pipeline')) return { title: 'Pipeline de traitement', category: 'Audit' };
  if (pathname.includes('/analysis')) return { title: 'Analyse de conformité', category: 'Rapports' };
  if (pathname.includes('/diff')) return { title: 'Comparaison de versions', category: 'Rapports' };
  if (pathname.startsWith('/dashboard/projects/new')) return { title: 'Nouveau projet', category: 'Projets' };
  if (pathname.startsWith('/dashboard/projects')) return { title: 'Projets de conformité', category: 'Gestion' };
  if (pathname.startsWith('/dashboard/corpus')) return { title: 'Codes & Articles de Loi', category: 'Référentiel' };
  if (pathname.startsWith('/dashboard/team')) return { title: 'Équipe & Accès', category: 'Organisation' };
  if (pathname.startsWith('/dashboard/admin/settings')) return { title: 'Paramètres système', category: 'Administration' };
  if (pathname.startsWith('/dashboard/settings')) return { title: 'Paramètres du compte', category: 'Mon Compte' };
  if (pathname.startsWith('/dashboard/admin/corpus')) return { title: 'Bibliothèque des Codes', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/sources/documents')) return { title: 'Archives Crawler', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/sources')) return { title: 'Sentinelle Réglementaire', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/rules')) return { title: 'Règles de scoring', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/models')) return { title: 'Modèles LLM', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/countries')) return { title: 'Pays & Juridictions', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/users')) return { title: 'Gestion des utilisateurs', category: 'Gouvernance' };
  if (pathname.startsWith('/dashboard/admin/audit')) return { title: 'Journaux d’audit', category: 'Gouvernance' };
  return { title: 'Tableau de bord', category: 'Plateforme' };
};

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout();
  const { data: currentUser, isLoading } = useMe();
  const isPlatformAdmin = Boolean(currentUser?.is_superuser || currentUser?.role === 'platform_admin');
  const canManageTeam = Boolean(currentUser?.role === 'org_admin');
  const visibleNavigation = navigation.filter((item) => item.href !== '/dashboard/team' || canManageTeam);
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Strict RBAC route guard: Platform Admin NEVER accesses user interfaces
  React.useEffect(() => {
    if (!isLoading && currentUser) {
      if (isPlatformAdmin) {
        if (
          pathname === '/dashboard' ||
          pathname.startsWith('/dashboard/projects') ||
          pathname.startsWith('/dashboard/team') ||
          pathname === '/dashboard/corpus'
        ) {
          router.replace('/dashboard/admin/corpus');
        } else if (pathname === '/dashboard/settings') {
          router.replace('/dashboard/admin/settings');
        }
      } else {
        if (pathname.startsWith('/dashboard/admin')) {
          router.replace('/dashboard');
        }
      }
    }
  }, [currentUser, isLoading, isPlatformAdmin, pathname, router]);

  const handleLogout = async () => {
    await logout.mutateAsync().catch(() => undefined);
    router.replace('/auth/login');
  };

  const navItems = isPlatformAdmin ? adminNavigation : visibleNavigation;
  const sectionTitle = isPlatformAdmin ? 'Administration' : 'Application';
  const logoHref = isPlatformAdmin ? '/dashboard/admin/corpus' : '/dashboard';

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen flex flex-col border-r border-slate-200 bg-white transition-all duration-300',
          collapsed ? 'lg:w-20' : 'lg:w-72',
          'w-72',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className={cn('flex items-center justify-between h-16 px-4 border-b border-slate-200', collapsed && 'lg:justify-center')}>
          {!collapsed && (
            <Link href={logoHref} className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-sovereign-500 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-slate-900 text-lg">ECE</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className={cn('hidden lg:inline-flex', collapsed && 'ml-auto')}
            aria-label={collapsed ? 'Étendre la barre latérale' : 'Réduire la barre latérale'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen(false)}
            className="lg:hidden"
            aria-label="Fermer le menu"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Navigation principale">
          {!collapsed && (
            <>
              <h3 className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {sectionTitle}
              </h3>
              {navItems.map((item) => {
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
              {navItems.map((item) => {
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
                    )}
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

        {/* User menu */}
        <div className={cn('p-4 border-t border-slate-200', collapsed && 'hidden')}>
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-sovereign-100 flex items-center justify-center">
              <span className="text-sm font-medium text-sovereign-600">
                {currentUser?.email ? currentUser.email.charAt(0).toUpperCase() : 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">
                {currentUser?.role ? currentUser.role.replace('_', ' ').toUpperCase() : 'Utilisateur'}
              </p>
              <p className="text-xs text-slate-500 truncate">{currentUser?.email || 'user@example.com'}</p>
            </div>
          </div>
          <Button variant="ghost" className="w-full justify-start" onClick={handleLogout} disabled={logout.isPending}>
            <LogOut className="h-4 w-4 mr-2" />
            {logout.isPending ? 'Déconnexion…' : 'Déconnexion'}
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main
        className={cn(
          'min-h-screen transition-all duration-300 ml-0',
          collapsed ? 'lg:ml-20' : 'lg:ml-72'
        )}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-white/95 backdrop-blur-md border-b border-slate-200">
          <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileOpen(true)}
                className="lg:hidden flex-shrink-0"
                aria-label="Ouvrir le menu"
              >
                <Menu className="h-5 w-5" />
              </Button>
              <span className="hidden sm:inline-flex text-xs font-semibold uppercase tracking-wider text-sovereign-600 bg-sovereign-50 px-2.5 py-1 rounded-md border border-sovereign-200/50">
                {getPageHeaderInfo(pathname).category}
              </span>
              <span className="hidden sm:inline text-slate-300">/</span>
              <h1 className="text-sm sm:text-base font-semibold text-slate-900 truncate">
                {getPageHeaderInfo(pathname).title}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100/80 border border-slate-200 text-xs text-slate-600">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Système opérationnel</span>
              </div>
              <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200">
                <div className="w-8 h-8 rounded-full bg-sovereign-600 text-white font-medium text-xs flex items-center justify-center">
                  {currentUser?.email ? currentUser.email.charAt(0).toUpperCase() : 'A'}
                </div>
                <div className="hidden md:block text-left text-xs">
                  <p className="font-semibold text-slate-800 leading-tight">{currentUser?.email || 'admin@ece.local'}</p>
                  <p className="text-slate-500 capitalize">{currentUser?.role?.replace('_', ' ') || 'Utilisateur'}</p>
                </div>
              </div>
            </div>
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

export default DashboardLayout;
