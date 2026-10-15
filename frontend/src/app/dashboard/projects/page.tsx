'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useProjects, useCreateProject } from '@/hooks/useApi';
import { Plus, Search } from 'lucide-react';
import Link from 'next/link';
import { cn, formatDateTime, getApiErrorMessage } from '@/lib/utils';
import { ErrorState, LoadingState } from '@/components/ui/feedback';
import { useState } from 'react';

const STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'active', label: 'Actif' },
  { value: 'completed', label: 'Terminé' },
  { value: 'archived', label: 'Archivé' },
];

const SECTORS = [
  'FinTech', 'E-commerce', 'Services Numériques', 'Santé', 'Éducation',
  'Administration', 'Télécoms', 'Énergie', 'Transport', 'Autre',
];

export default function ProjectsPage() {
  const { data: projects, isLoading, isError, error, refetch } = useProjects();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showNewProject, setShowNewProject] = useState(false);

  const filteredProjects = projects?.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sector.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  }) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Projets</h1>
          <p className="page-subtitle">Gérez vos projets d'audit de conformité</p>
        </div>
        <Button onClick={() => setShowNewProject(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau projet
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher par nom, secteur..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Projects Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <LoadingState label="Chargement des projets…" />
          ) : isError ? (
            <ErrorState message={getApiErrorMessage(error, 'Impossible de charger les projets.')} onRetry={() => void refetch()} />
          ) : filteredProjects.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Projet</TableHead>
                  <TableHead>Pays</TableHead>
                  <TableHead>Secteur</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Score de risque</TableHead>
                  <TableHead>Dernière analyse</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProjects.map((project) => (
                  <TableRow key={project.id}>
                    <TableCell>
                      <Link href={`/dashboard/projects/${project.id}`} className="font-medium text-sovereign-600 hover:underline">
                        {project.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant={project.country_code.toLowerCase() === 'bj' ? 'default' : 'secondary'}>
                        {project.country_code.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>{project.sector}</TableCell>
                    <TableCell>
                      <Badge variant={project.status === 'active' ? 'conforme' : project.status === 'completed' ? 'modere' : 'secondary'}>
                        {project.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {project.risk_score !== null ? (
                        <span className={cn('font-medium', project.risk_score > 70 ? 'text-danger-600' : project.risk_score > 40 ? 'text-warning-600' : 'text-success-600')}>
                          {project.risk_score}/100
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {project.last_analysis ? formatDateTime(project.last_analysis) : <span className="text-slate-400">—</span>}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/dashboard/projects/${project.id}`} className="text-sm text-sovereign-600 hover:underline mr-3">
                        Ouvrir
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <div className="h-12 w-12 text-slate-300 mx-auto mb-4">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun projet</h3>
              <p className="text-slate-500 mb-4">Commencez par créer votre premier projet d'audit de conformité.</p>
              <Button onClick={() => setShowNewProject(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Créer un projet
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* New Project Modal */}
      {showNewProject && (
        <NewProjectModal onClose={() => setShowNewProject(false)} onSuccess={() => setShowNewProject(false)} />
      )}
    </div>
  );
}

function NewProjectModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const createProject = useCreateProject();
  const [formData, setFormData] = useState({
    name: '',
    country_code: 'BJ',
    sector: '',
    treatments: [] as string[],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const TREATMENT_OPTIONS = [
    { value: 'data_protection', label: 'Protection des données personnelles' },
    { value: 'payment_services', label: 'Services de paiement / Monnaie électronique' },
    { value: 'ecommerce', label: 'Commerce électronique' },
    { value: 'cybersecurity', label: 'Cybersécurité' },
    { value: 'digital_identity', label: 'Identité numérique' },
    { value: 'data_retention', label: 'Conservation des données' },
    { value: 'subcontracting', label: 'Sous-traitance' },
    { value: 'incident_notification', label: 'Notification d\'incidents' },
    { value: 'aml_cft', label: 'Lutte contre le blanchiment (LCB/FT)' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = 'Le nom est requis';
    if (!formData.sector.trim()) newErrors.sector = 'Le secteur est requis';
    if (formData.treatments.length === 0) newErrors.treatments = 'Sélectionnez au moins un type de traitement';
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await createProject.mutateAsync({
        name: formData.name,
        country_code: formData.country_code,
        sector: formData.sector,
        treatments: formData.treatments,
      });
      onSuccess();
    } catch (err: any) {
      setErrors({ submit: getApiErrorMessage(err, 'La création du projet a échoué. Vérifiez les champs puis réessayez.') });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Nouveau projet</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {errors.submit && (
            <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm">
              {errors.submit}
            </div>
          )}

          <div>
            <label className="label">Nom du projet *</label>
            <Input
              placeholder="ex: StockOpti — Bénin"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={errors.name ? 'input-error' : ''}
            />
            {errors.name && <p className="mt-1 text-sm text-danger-600">{errors.name}</p>}
          </div>

          <div>
            <label className="label">Pays cible *</label>
            <Select value={formData.country_code} onValueChange={(v) => setFormData({ ...formData, country_code: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BJ">🇧🇯 Bénin (actif)</SelectItem>
                <SelectItem value="SN" disabled>🇸🇳 Sénégal (bientôt)</SelectItem>
                <SelectItem value="CI" disabled>🇨🇮 Côte d'Ivoire (bientôt)</SelectItem>
                <SelectItem value="TG" disabled>🇹🇬 Togo (bientôt)</SelectItem>
                <SelectItem value="BF" disabled>🇧🇫 Burkina Faso (bientôt)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="label">Secteur d'activité *</label>
            <Select value={formData.sector} onValueChange={(v) => setFormData({ ...formData, sector: v })}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionnez un secteur" />
              </SelectTrigger>
              <SelectContent>
                {SECTORS.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.sector && <p className="mt-1 text-sm text-danger-600">{errors.sector}</p>}
          </div>

          <div>
            <label className="label">Types de traitement / services *</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {TREATMENT_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                  <input
                    type="checkbox"
                    checked={formData.treatments.includes(opt.value)}
                    onChange={(e) => setFormData({
                      ...formData,
                      treatments: e.target.checked
                        ? [...formData.treatments, opt.value]
                        : formData.treatments.filter(t => t !== opt.value)
                    })}
                    className="h-4 w-4 text-sovereign-500 border-slate-300 rounded focus:ring-sovereign-500"
                  />
                  <span className="text-sm text-slate-700">{opt.label}</span>
                </label>
              ))}
            </div>
            {errors.treatments && <p className="mt-1 text-sm text-danger-600">{errors.treatments}</p>}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <Button type="button" variant="secondary" onClick={onClose} disabled={createProject.isPending}>
              Annuler
            </Button>
            <Button type="submit" disabled={createProject.isPending}>
              {createProject.isPending ? 'Création...' : 'Créer le projet'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
