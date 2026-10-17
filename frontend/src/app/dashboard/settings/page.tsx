'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ErrorState, LoadingState } from '@/components/ui/feedback';
import { Input } from '@/components/ui/input';
import { useMe, useOrganization, useUpdateMe, useUpdateOrganization } from '@/hooks/useApi';
import { getApiErrorMessage } from '@/lib/utils';

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } })?.response?.status === 404;
}

export default function SettingsPage() {
  const userQuery = useMe();
  const organizationQuery = useOrganization();
  const updateAccount = useUpdateMe();
  const updateOrganization = useUpdateOrganization();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [organizationName, setOrganizationName] = React.useState('');
  const [accountError, setAccountError] = React.useState('');
  const [organizationError, setOrganizationError] = React.useState('');

  React.useEffect(() => {
    if (userQuery.data) setEmail(userQuery.data.email);
  }, [userQuery.data]);

  React.useEffect(() => {
    if (organizationQuery.data) setOrganizationName(organizationQuery.data.name);
  }, [organizationQuery.data]);

  const canEditOrganization = Boolean(
    userQuery.data?.is_superuser || userQuery.data?.role === 'platform_admin' || userQuery.data?.role === 'org_admin'
  );

  const saveAccount = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAccountError('');
    try {
      await updateAccount.mutateAsync({ email, ...(password ? { password } : {}) });
      setPassword('');
    } catch (error) {
      setAccountError(getApiErrorMessage(error, 'Impossible de mettre à jour le compte.'));
    }
  };

  const saveOrganization = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOrganizationError('');
    try {
      await updateOrganization.mutateAsync(organizationName);
    } catch (error) {
      setOrganizationError(getApiErrorMessage(error, 'Impossible de mettre à jour l’organisation.'));
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <h1 className="page-title">Paramètres</h1>
        <p className="page-subtitle">Gérez les informations de votre compte et de votre organisation.</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Mon compte</CardTitle>
          <p className="text-sm text-slate-500">Modifiez votre adresse e-mail ou définissez un nouveau mot de passe.</p>
        </CardHeader>
        <CardContent>
          {userQuery.isLoading ? <LoadingState label="Chargement du compte…" /> : userQuery.isError ? (
            <ErrorState message={getApiErrorMessage(userQuery.error, 'Impossible de charger le compte.')} onRetry={() => void userQuery.refetch()} />
          ) : (
            <form onSubmit={saveAccount} className="space-y-4">
              <label className="block space-y-1.5 text-sm font-medium">Adresse e-mail
                <Input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
              </label>
              <label className="block space-y-1.5 text-sm font-medium">Nouveau mot de passe <span className="font-normal text-slate-500">(facultatif)</span>
                <Input type="password" autoComplete="new-password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Laisser vide pour ne pas le changer" />
              </label>
              {accountError && <p role="alert" className="text-sm text-danger-700">{accountError}</p>}
              {updateAccount.isSuccess && <p role="status" className="text-sm text-success-700">Les informations du compte ont été enregistrées.</p>}
              <Button type="submit" disabled={updateAccount.isPending}>{updateAccount.isPending ? 'Enregistrement…' : 'Enregistrer le compte'}</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Organisation</CardTitle>
          <p className="text-sm text-slate-500">Le nom est partagé avec les membres de votre organisation.</p>
        </CardHeader>
        <CardContent>
          {organizationQuery.isLoading ? <LoadingState label="Chargement de l’organisation…" /> : organizationQuery.isError && !isNotFound(organizationQuery.error) ? (
            <ErrorState message={getApiErrorMessage(organizationQuery.error, 'Impossible de charger l’organisation.')} onRetry={() => void organizationQuery.refetch()} />
          ) : organizationQuery.data ? (
            <form onSubmit={saveOrganization} className="space-y-4">
              <label className="block space-y-1.5 text-sm font-medium">Nom de l’organisation
                <Input required minLength={1} maxLength={255} value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} disabled={!canEditOrganization} />
              </label>
              <p className="text-sm text-slate-500">Offre actuelle : {organizationQuery.data.plan}</p>
              {organizationError && <p role="alert" className="text-sm text-danger-700">{organizationError}</p>}
              {updateOrganization.isSuccess && <p role="status" className="text-sm text-success-700">Le nom de l’organisation a été enregistré.</p>}
              {canEditOrganization && <Button type="submit" disabled={updateOrganization.isPending}>{updateOrganization.isPending ? 'Enregistrement…' : 'Enregistrer l’organisation'}</Button>}
              {!canEditOrganization && <p className="text-sm text-slate-500">Seul un administrateur de l’organisation peut modifier son nom.</p>}
            </form>
          ) : (
            <p className="text-sm text-slate-600">Aucune organisation n’est encore associée à ce compte. Elle sera créée lorsque vous lancerez votre premier projet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
