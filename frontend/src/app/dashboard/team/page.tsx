'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ErrorState, LoadingState } from '@/components/ui/feedback';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useCreateOrganizationMember, useOrganizationMembers } from '@/hooks/useApi';
import { useMe } from '@/hooks/useApi';
import { formatDateTime, getApiErrorMessage } from '@/lib/utils';

const MEMBER_ROLES = [
  { value: 'analyst', label: 'Analyste' },
  { value: 'reader', label: 'Lecteur' },
  { value: 'external_auditor', label: 'Auditeur externe' },
  { value: 'org_admin', label: 'Administrateur organisation' },
];

const ROLE_LABELS = Object.fromEntries(MEMBER_ROLES.map(({ value, label }) => [value, label]));

export default function TeamPage() {
  const userQuery = useMe();
  const canManageTeam = Boolean(userQuery.data?.is_superuser || userQuery.data?.role === 'platform_admin' || userQuery.data?.role === 'org_admin');
  const membersQuery = useOrganizationMembers(canManageTeam);
  const createMember = useCreateOrganizationMember();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [role, setRole] = React.useState('analyst');
  const [formError, setFormError] = React.useState('');

  if (userQuery.isLoading) return <LoadingState label="Vérification des droits…" />;
  if (!canManageTeam) {
    return <ErrorState message="La gestion de l’équipe est réservée aux administrateurs de l’organisation." />;
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    try {
      await createMember.mutateAsync({ email, password, role });
      setEmail('');
      setPassword('');
      setRole('analyst');
    } catch (error) {
      setFormError(getApiErrorMessage(error, 'Impossible d’ajouter ce membre.'));
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="page-title">Équipe</h1>
        <p className="page-subtitle">Gérez les comptes et les rôles des membres de votre organisation.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Ajouter un membre</CardTitle>
          <p className="text-sm text-slate-500">Le compte sera rattaché à votre organisation. Transmettez-lui son mot de passe initial de façon sécurisée.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1.5 text-sm font-medium">Adresse e-mail
              <Input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <label className="space-y-1.5 text-sm font-medium">Mot de passe initial
              <Input type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <label className="space-y-1.5 text-sm font-medium">Rôle
              <select className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" value={role} onChange={(event) => setRole(event.target.value)}>
                {MEMBER_ROLES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="flex items-end">
              <Button type="submit" disabled={createMember.isPending}>
                {createMember.isPending ? 'Ajout…' : 'Ajouter à l’équipe'}
              </Button>
            </div>
          </form>
          {formError && <p role="alert" className="mt-3 text-sm text-danger-700">{formError}</p>}
          {createMember.isSuccess && <p role="status" className="mt-3 text-sm text-success-700">Le membre a été ajouté à votre organisation.</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-lg">Membres de l’organisation</CardTitle></CardHeader>
        <CardContent>
          {membersQuery.isLoading ? <LoadingState label="Chargement de l’équipe…" /> : membersQuery.isError ? (
            <ErrorState message={getApiErrorMessage(membersQuery.error, 'Impossible de charger les membres de l’organisation.')} onRetry={() => void membersQuery.refetch()} />
          ) : membersQuery.data?.length ? (
            <Table>
              <TableHeader><TableRow><TableHead>Compte</TableHead><TableHead>Rôle</TableHead><TableHead>Statut</TableHead><TableHead>Ajouté le</TableHead></TableRow></TableHeader>
              <TableBody>
                {membersQuery.data.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell className="font-medium">{member.email}</TableCell>
                    <TableCell>{ROLE_LABELS[member.role] || (member.role === 'platform_admin' ? 'Administrateur plateforme' : member.role)}</TableCell>
                    <TableCell><Badge variant={member.is_active ? 'conforme' : 'secondary'}>{member.is_active ? 'Actif' : 'Inactif'}</Badge></TableCell>
                    <TableCell className="text-sm text-slate-500">{formatDateTime(member.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <p className="py-8 text-center text-sm text-slate-500">Aucun membre dans cette organisation.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
