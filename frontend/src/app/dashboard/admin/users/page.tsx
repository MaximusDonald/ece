'use client';

import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminUsers, useCreatePlatformAdmin } from '@/hooks/useApi';
import { formatDateTime, getApiErrorMessage } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/feedback';
import {
  Users,
  UserPlus,
  ShieldAlert,
  Search,
  CheckCircle2,
  Mail,
  Lock,
  Building2,
  Calendar,
  Clock,
  Shield,
  Copy,
  Check,
} from 'lucide-react';

const ROLE_CONFIG: Record<string, { label: string; badgeClass: string }> = {
  org_admin: {
    label: 'Admin organisation',
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  analyst: {
    label: 'Analyste',
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  },
  reader: {
    label: 'Lecteur',
    badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
  },
  external_auditor: {
    label: 'Auditeur externe',
    badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  platform_admin: {
    label: 'Admin plateforme',
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200 font-semibold',
  },
};

export default function AdminUsersPage() {
  const { data: users, isLoading, isError, refetch } = useAdminUsers();
  const createAdmin = useCreatePlatformAdmin();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [formError, setFormError] = React.useState('');
  const [searchTerm, setSearchTerm] = React.useState('');
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const submitAdmin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    try {
      await createAdmin.mutateAsync({ email, password });
      setEmail('');
      setPassword('');
    } catch (error) {
      setFormError(getApiErrorMessage(error, 'Impossible de créer cet administrateur.'));
    }
  };

  const filteredUsers = React.useMemo(() => {
    if (!users) return [];
    if (!searchTerm.trim()) return users;
    const term = searchTerm.toLowerCase();
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(term) ||
        u.role.toLowerCase().includes(term) ||
        (u.org_id && u.org_id.toLowerCase().includes(term))
    );
  }, [users, searchTerm]);

  const totalUsers = users?.length || 0;
  const platformAdminsCount = users?.filter((u) => u.role === 'platform_admin').length || 0;
  const activeUsersCount = users?.filter((u) => u.is_active).length || 0;

  return (
    <div className="space-y-6">
      {/* Top Header Summary */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Gestion des utilisateurs</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Supervisez les accès, affectations d'organisations et privilèges de la plateforme.
          </p>
        </div>

        {/* Quick KPI stats */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 shadow-xs">
            <Users className="w-4 h-4 text-slate-500" />
            <div className="text-xs">
              <span className="text-slate-500 block leading-none">Total</span>
              <span className="font-bold text-slate-900 text-sm">{totalUsers}</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 shadow-xs">
            <Shield className="w-4 h-4 text-rose-500" />
            <div className="text-xs">
              <span className="text-slate-500 block leading-none">Admins</span>
              <span className="font-bold text-slate-900 text-sm">{platformAdminsCount}</span>
            </div>
          </div>
          <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 shadow-xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <div className="text-xs">
              <span className="text-slate-500 block leading-none">Actifs</span>
              <span className="font-bold text-slate-900 text-sm">{activeUsersCount}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Admin Creation Card */}
      <Card className="border-slate-200/80 shadow-xs overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-sovereign-500 via-sovereign-600 to-indigo-600" />
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-sovereign-50 flex items-center justify-center text-sovereign-600">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                Créer un administrateur de gouvernance
              </CardTitle>
              <CardDescription className="text-xs text-slate-500">
                Ce compte aura un accès complet aux réglages souverains, LLMs, sources juridiques et utilisateurs.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitAdmin} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_auto] gap-4 items-end">
              <div className="space-y-1.5">
                <Label htmlFor="admin-email" className="text-xs font-semibold text-slate-700">
                  Adresse e-mail professionnelle
                </Label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    id="admin-email"
                    type="email"
                    placeholder="admin@organisation.gov"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9 h-10 text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="admin-password" className="text-xs font-semibold text-slate-700">
                  Mot de passe temporaire
                </Label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    id="admin-password"
                    type="password"
                    placeholder="Minimum 8 caractères"
                    autoComplete="new-password"
                    minLength={8}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9 h-10 text-sm"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={createAdmin.isPending}
                className="h-10 px-5 bg-sovereign-600 hover:bg-sovereign-700 text-white font-medium shadow-xs flex items-center justify-center gap-2"
              >
                <UserPlus className="w-4 h-4" />
                <span>{createAdmin.isPending ? 'Création en cours…' : 'Créer l’administrateur'}</span>
              </Button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            {createAdmin.isSuccess && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>Le compte administrateur a été créé avec succès.</span>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Users Table Card */}
      <Card className="border-slate-200/80 shadow-xs">
        <CardHeader className="py-4 px-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-semibold text-slate-900">Répertoire des utilisateurs</CardTitle>
            <CardDescription className="text-xs text-slate-500">
              {filteredUsers.length} utilisateur{filteredUsers.length > 1 ? 's' : ''} répertorié{filteredUsers.length > 1 ? 's' : ''}
            </CardDescription>
          </div>

          {/* Search bar */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              type="text"
              placeholder="Filtrer par email, rôle, id…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 h-9 text-xs"
            />
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="py-16">
              <LoadingState label="Chargement des utilisateurs en cours…" />
            </div>
          ) : isError ? (
            <div className="py-12 text-center">
              <ShieldAlert className="w-10 h-10 text-rose-500 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-900">Impossible de charger la liste des utilisateurs</p>
              <p className="text-xs text-slate-500 mt-1 mb-4">Vérifiez votre connexion au serveur ou vos droits d'accès.</p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Réessayer
              </Button>
            </div>
          ) : filteredUsers.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/70 hover:bg-slate-50/70">
                    <TableHead className="w-[320px] font-semibold text-slate-700 text-xs py-3.5">Utilisateur</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-xs py-3.5">Rôle</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-xs py-3.5">Organisation</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-xs py-3.5">Statut</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-xs py-3.5">Dernière connexion</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-xs py-3.5">Date d'inscription</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => {
                    const roleInfo = ROLE_CONFIG[user.role] || {
                      label: user.role,
                      badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
                    };

                    return (
                      <TableRow key={user.id} className="hover:bg-slate-50/60 transition-colors">
                        {/* User email + ID */}
                        <TableCell className="py-3.5">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-full bg-sovereign-100 border border-sovereign-200/60 text-sovereign-700 font-bold text-xs flex items-center justify-center flex-shrink-0">
                              {user.email.charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="font-medium text-sm text-slate-900 truncate">{user.email}</p>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="font-mono text-[11px] text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                  {user.id.slice(0, 8)}...
                                </span>
                                <button
                                  type="button"
                                  onClick={() => handleCopyId(user.id)}
                                  title="Copier l'identifiant"
                                  className="text-slate-400 hover:text-slate-700 transition-colors p-0.5"
                                >
                                  {copiedId === user.id ? (
                                    <Check className="w-3 h-3 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3 h-3" />
                                  )}
                                </button>
                              </div>
                            </div>
                          </div>
                        </TableCell>

                        {/* Role */}
                        <TableCell className="py-3.5">
                          <Badge variant="outline" className={`text-xs px-2.5 py-0.5 font-medium ${roleInfo.badgeClass}`}>
                            {roleInfo.label}
                          </Badge>
                        </TableCell>

                        {/* Organisation */}
                        <TableCell className="py-3.5">
                          {user.org_id ? (
                            <div className="flex items-center gap-1.5 text-xs text-slate-700 font-mono">
                              <Building2 className="w-3.5 h-3.5 text-slate-400" />
                              <span>{user.org_id.slice(0, 8)}...</span>
                            </div>
                          ) : (
                            <span className="text-slate-400 text-xs italic">Aucune</span>
                          )}
                        </TableCell>

                        {/* Statut */}
                        <TableCell className="py-3.5">
                          {user.is_active ? (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                              Actif
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                              Inactif
                            </span>
                          )}
                        </TableCell>

                        {/* Dernière connexion */}
                        <TableCell className="py-3.5 text-xs text-slate-600 whitespace-nowrap">
                          {user.last_login ? (
                            <div className="flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-slate-400" />
                              <span>{formatDateTime(user.last_login)}</span>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Jamais connecté</span>
                          )}
                        </TableCell>

                        {/* Créé le */}
                        <TableCell className="py-3.5 text-xs text-slate-600 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5 text-slate-400" />
                            <span>{formatDateTime(user.created_at)}</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-700">Aucun utilisateur trouvé</p>
              <p className="text-xs text-slate-400 mt-1">Aucun compte ne correspond à votre recherche.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
