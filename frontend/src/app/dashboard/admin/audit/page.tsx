'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { useAdminAuditLogs } from '@/hooks/useApi';
import { formatDateTime } from '@/lib/utils';
import { Search, Filter } from 'lucide-react';
import { useState } from 'react';

const ENTITY_TYPES = [
  { value: '', label: 'Tous' },
  { value: 'legal_source', label: 'Source juridique' },
  { value: 'scoring_rule', label: 'Règle de scoring' },
  { value: 'llm_config', label: 'Modèle LLM' },
  { value: 'country_module', label: 'Module pays' },
  { value: 'user', label: 'Utilisateur' },
  { value: 'project', label: 'Projet' },
  { value: 'document', label: 'Document' },
  { value: 'report_version', label: 'Rapport' },
];

const ACTIONS = [
  { value: '', label: 'Toutes' },
  { value: 'create_source', label: 'Création source' },
  { value: 'update_source', label: 'Modification source' },
  { value: 'verify_source', label: 'Vérification source' },
  { value: 'create_rule', label: 'Création règle' },
  { value: 'update_rule', label: 'Modification règle' },
  { value: 'create_model', label: 'Création modèle' },
  { value: 'update_model', label: 'Modification modèle' },
  { value: 'update_country', label: 'Activation pays' },
  { value: 'create_project', label: 'Création projet' },
  { value: 'upload_document', label: 'Téléversement document' },
  { value: 'incremental_update', label: 'Mise à jour incrémentale' },
];

export default function AdminAuditPage() {
  const [filters, setFilters] = useState({
    entity_type: '',
    action: '',
    search: '',
  });
  const { data: logs, isLoading } = useAdminAuditLogs(filters);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Journaux d'audit</h1>
          <p className="page-subtitle">Traçabilité immuable de toutes les actions sensibles</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher par utilisateur, entité, action..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-10"
              />
            </div>
            <Select value={filters.entity_type} onValueChange={(v) => setFilters({ ...filters, entity_type: v })}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="Type d'entité" />
              </SelectTrigger>
              <SelectContent>
                {ENTITY_TYPES.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.action} onValueChange={(v) => setFilters({ ...filters, action: v })}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="Action" />
              </SelectTrigger>
              <SelectContent>
                {ACTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : logs && logs.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Horodatage</TableHead>
                  <TableHead>Utilisateur</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entité</TableHead>
                  <TableHead>ID Entité</TableHead>
                  <TableHead>Détails</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-sm whitespace-nowrap">
                      {formatDateTime(log.timestamp)}
                    </TableCell>
                    <TableCell>
                      {log.user_id ? (
                        <span className="font-mono text-sm">{log.user_id.slice(0, 8)}...</span>
                      ) : (
                        <span className="text-slate-400 text-sm">Système</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{log.action}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">{log.entity_type}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {log.entity_id ? log.entity_id.slice(0, 12) + '...' : '—'}
                    </TableCell>
                    <TableCell className="max-w-[300px]">
                      {log.diff ? (
                        <details className="group">
                          <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
                            Voir les changements ({Object.keys(log.diff).length} champs)
                          </summary>
                          <pre className="mt-1 p-2 bg-slate-50 rounded text-xs font-mono overflow-x-auto max-h-32 overflow-y-auto">
                            {JSON.stringify(log.diff, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun journal</h3>
              <p className="text-slate-500">Les actions sensibles apparaîtront ici.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
