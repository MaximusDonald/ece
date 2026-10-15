'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminCountries, useUpdateCountry } from '@/hooks/useApi';
import { Globe, CheckCircle, X, Edit2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';

const COUNTRIES = [
  { code: 'BJ', name: 'Bénin', flag: '🇧🇯' },
  { code: 'SN', name: 'Sénégal', flag: '🇸🇳' },
  { code: 'CI', name: "Côte d'Ivoire", flag: '🇨🇮' },
  { code: 'TG', name: 'Togo', flag: '🇹🇬' },
  { code: 'BF', name: 'Burkina Faso', flag: '🇧🇫' },
  { code: 'NE', name: 'Niger', flag: '🇳🇪' },
  { code: 'ML', name: 'Mali', flag: '🇲🇱' },
  { code: 'GN', name: 'Guinée', flag: '🇬🇳' },
  { code: 'GW', name: 'Guinée-Bissau', flag: '🇬🇼' },
  { code: 'CV', name: 'Cap-Vert', flag: '🇨🇻' },
  { code: 'GH', name: 'Ghana', flag: '🇬🇭' },
  { code: 'NG', name: 'Nigéria', flag: '🇳🇬' },
  { code: 'LR', name: 'Libéria', flag: '🇱🇷' },
  { code: 'SL', name: 'Sierra Leone', flag: '🇸🇱' },
  { code: 'GM', name: 'Gambie', flag: '🇬🇲' },
];

export default function AdminCountriesPage() {
  const { data: countries, isLoading, refetch } = useAdminCountries();
  const updateCountry = useUpdateCountry();
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [editActive, setEditActive] = useState(false);

  const handleToggle = async (code: string, active: boolean) => {
    try {
      await updateCountry.mutateAsync({ code, data: { is_active: active } });
      refetch();
    } catch (err) {
      toast({ title: 'Mise à jour impossible', description: 'Le statut du pays n’a pas pu être modifié.', variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Pays / Juridictions</h1>
          <p className="page-subtitle">Activez les modules pays et suivez l'ingestion du corpus</p>
        </div>
      </div>

      {/* Countries Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : countries && countries.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pays</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Sources ingérées</TableHead>
                  <TableHead>Dernière sync</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {COUNTRIES.map((country) => {
                  const module = countries.find(c => c.country_code === country.code);
                  const isActive = module?.is_active || false;
                  const sourcesCount = module?.legal_sources_count || 0;
                  const lastSync = module?.last_sync;
                  return (
                    <TableRow key={country.code}>
                      <TableCell>
                        <span className="text-2xl mr-2">{country.flag}</span>
                        <span className="font-medium">{country.name}</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-sm">{country.code}</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={isActive ? 'conforme' : 'secondary'}>
                          {isActive ? 'Actif' : 'Inactif'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{sourcesCount} textes</span>
                      </TableCell>
                      <TableCell>
                        {lastSync ? new Date(lastSync).toLocaleDateString('fr-FR') : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleToggle(country.code, !isActive)}
                          disabled={updateCountry.isPending}
                        >
                          {isActive ? <X className="h-4 w-4 text-danger-600" /> : <CheckCircle className="h-4 w-4 text-success-600" />}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <Globe className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun pays configuré</h3>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info */}
      <Card className="border-sovereign-200 bg-sovereign-50">
        <CardContent className="p-6">
          <h3 className="font-medium text-sovereign-800 mb-2">Note</h3>
          <p className="text-sovereign-600 text-sm">
            Seuls les pays activés apparaissent dans le sélecteur de création de projet. 
            Le Bénin est pré-activé et pré-peuplé avec le corpus juridique initial.
            L'activation d'un nouveau pays nécessite l'ingestion préalable de ses sources juridiques.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
