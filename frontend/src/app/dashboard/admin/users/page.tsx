'use client';

import * as React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminUsers, useCreatePlatformAdmin } from '@/hooks/useApi';
import { formatDateTime, getApiErrorMessage } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { LoadingState } from '@/components/ui/feedback';

const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Admin organisation',
  analyst: 'Analyste',
  reader: 'Lecteur',
  external_auditor: 'Auditeur externe',
  platform_admin: 'Admin plateforme',
};

const ROLE_BADGES: Record<string, string> = {
  org_admin: 'default',
  analyst: 'outline',
  reader: 'secondary',
  external_auditor: 'warning',
  platform_admin: 'destructive',
};

export default function AdminUsersPage() {
  const { data: users, isLoading, isError, refetch } = useAdminUsers();
  const createAdmin = useCreatePlatformAdmin();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [formError, setFormError] = React.useState('');

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Utilisateurs</h1>
        <p className="page-subtitle">Vue d'ensemble de tous les utilisateurs de la plateforme</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Créer un administrateur de gouvernance</CardTitle>
          <p className="text-sm text-slate-500">Ce compte aura accès aux réglages globaux et pourra créer d’autres administrateurs.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitAdmin} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
            <label className="space-y-1.5 text-sm font-medium">Adresse e-mail
              <Input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="space-y-1.5 text-sm font-medium">Mot de passe temporaire
              <Input type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <Button type="submit" disabled={createAdmin.isPending}>
              {createAdmin.isPending ? 'Création…' : 'Créer l’administrateur'}
            </Button>
          </form>
          {formError && <p role="alert" className="mt-3 text-sm text-danger-700">{formError}</p>}
          {createAdmin.isSuccess && <p role="status" className="mt-3 text-sm text-success-700">Le compte administrateur a été créé.</p>}
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <LoadingState label="Chargement des comptes…" />
          ) : isError ? (
            <div className="py-8 text-center">
              <p className="mb-3 text-sm text-danger-700">Impossible de charger la liste des utilisateurs.</p>
              <Button variant="outline" onClick={() => refetch()}>Réessayer</Button>
            </div>
          ) : users && users.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Utilisateur</TableHead>
                  <TableHead>Rôle</TableHead>
                  <TableHead>Organisation</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Dernière connexion</TableHead>
                  <TableHead>Créé le</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{user.email}</p>
                        <p className="text-xs text-slate-500 font-mono">{user.id.slice(0, 8)}...</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={ROLE_BADGES[user.role] || 'outline'}>
                        {ROLE_LABELS[user.role] || user.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {user.org_id ? (
                        <span className="font-mono text-sm">{user.org_id.slice(0, 8)}...</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? 'conforme' : 'secondary'}>
                        {user.is_active ? 'Actif' : 'Inactif'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {user.last_login ? formatDateTime(user.last_login) : 'Jamais'}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {formatDateTime(user.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun utilisateur</h3>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
