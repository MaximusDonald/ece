'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminUsers } from '@/hooks/useApi';
import { formatDateTime } from '@/lib/utils';

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
  const { data: users, isLoading } = useAdminUsers();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Utilisateurs</h1>
        <p className="page-subtitle">Vue d'ensemble de tous les utilisateurs de la plateforme</p>
      </div>

      {/* Users Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
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