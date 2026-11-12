'use client';

import * as React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ErrorState, LoadingState } from '@/components/ui/feedback';
import { Input } from '@/components/ui/input';
import { useMe, useUpdateMe } from '@/hooks/useApi';
import { getApiErrorMessage } from '@/lib/utils';
import {
  Shield,
  Key,
  Database,
  Globe,
  History,
  CheckCircle2,
  AlertCircle,
  FileText,
} from 'lucide-react';

export default function AdminSettingsPage() {
  const userQuery = useMe();
  const updateAccount = useUpdateMe();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [accountError, setAccountError] = React.useState('');
  const [successMessage, setSuccessMessage] = React.useState('');

  React.useEffect(() => {
    if (userQuery.data) {
      setEmail(userQuery.data.email);
    }
  }, [userQuery.data]);

  const saveAccount = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAccountError('');
    setSuccessMessage('');

    if (password && password.length < 8) {
      setAccountError('Le mot de passe doit comporter au moins 8 caractères.');
      return;
    }

    if (password && password !== confirmPassword) {
      setAccountError('Les deux mots de passe ne correspondent pas.');
      return;
    }

    try {
      await updateAccount.mutateAsync({
        email: email.trim(),
        ...(password ? { password } : {}),
      });
      setPassword('');
      setConfirmPassword('');
      setSuccessMessage('Compte administrateur mis à jour avec succès.');
    } catch (error) {
      setAccountError(getApiErrorMessage(error, 'Impossible de mettre à jour le compte administrateur.'));
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sovereign-50 border border-sovereign-200 flex items-center justify-center text-sovereign-600">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h1 className="page-title">Paramètres d’administration</h1>
            <p className="page-subtitle">
              Gestion du profil administrateur, sécurité du système et surveillance des services souverains.
            </p>
          </div>
        </div>
      </header>

      {/* Isolation Notice */}
      <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/80 text-amber-900 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="space-y-1 text-sm">
          <p className="font-semibold text-amber-900">
            Cloisonnement strict des accès (Gouvernance vs Espaces Utilisateurs)
          </p>
          <p className="text-amber-800 leading-relaxed">
            Ce compte est exclusivement dédié à l’administration globale (gestion du corpus juridique, sentinelle réglementaire, règles de scoring, modèles d’IA et comptes utilisateurs).
            Conformément à la politique de sécurité ECE, <strong>l’administrateur plateforme n’a aucun accès aux interfaces utilisateurs ni aux projets métiers</strong>. Pour tester ou réaliser des audits de projet, veuillez utiliser un compte utilisateur standard.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Mon Compte Administrateur */}
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Key className="w-4 h-4 text-sovereign-600" />
                Compte Administrateur
              </CardTitle>
              <Badge variant="outline" className="border-sovereign-300 text-sovereign-700 bg-sovereign-50">
                PLATFORM ADMIN
              </Badge>
            </div>
            <p className="text-sm text-slate-500">
              Mettez à jour vos identifiants d’accès au panneau d’administration.
            </p>
          </CardHeader>
          <CardContent>
            {userQuery.isLoading ? (
              <LoadingState label="Chargement du compte administrateur…" />
            ) : userQuery.isError ? (
              <ErrorState
                message={getApiErrorMessage(userQuery.error, 'Impossible de charger le compte.')}
                onRetry={() => void userQuery.refetch()}
              />
            ) : (
              <form onSubmit={saveAccount} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">Adresse e-mail</label>
                  <Input
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">
                      Nouveau mot de passe <span className="font-normal text-slate-500">(optionnel)</span>
                    </label>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="8 caractères min."
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">
                      Confirmer le mot de passe
                    </label>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Répétez le mot de passe"
                      disabled={!password}
                    />
                  </div>
                </div>

                {accountError && (
                  <div className="p-3 rounded-lg bg-danger-50 border border-danger-200 text-sm text-danger-800">
                    {accountError}
                  </div>
                )}
                {successMessage && (
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    {successMessage}
                  </div>
                )}

                <div className="pt-2">
                  <Button type="submit" disabled={updateAccount.isPending}>
                    {updateAccount.isPending ? 'Enregistrement…' : 'Enregistrer les modifications'}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Accès Rapides Gouvernance */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-600" />
                Gouvernance Rapide
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link
                href="/dashboard/admin/rules"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-100 transition-colors text-sm text-slate-700 border border-slate-100"
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-sovereign-600" />
                  <span>Règles de scoring</span>
                </div>
                <span className="text-xs text-slate-400">Modifier</span>
              </Link>

              <Link
                href="/dashboard/admin/audit"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-100 transition-colors text-sm text-slate-700 border border-slate-100"
              >
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-sovereign-600" />
                  <span>Journaux d’audit</span>
                </div>
                <span className="text-xs text-slate-400">Consulter</span>
              </Link>

              <Link
                href="/dashboard/admin/sources"
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-100 transition-colors text-sm text-slate-700 border border-slate-100"
              >
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-sovereign-600" />
                  <span>Sentinelle veille</span>
                </div>
                <span className="text-xs text-slate-400">Surveiller</span>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-600" />
                Infrastructure ECE
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">API REST Backend</span>
                <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Opérationnel
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">PostgreSQL / pgvector</span>
                <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  1 536 dim / Actif
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Master Corpus</span>
                <span className="text-slate-800 font-medium">2 142 articles</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Stockage MinIO</span>
                <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Connecté
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
