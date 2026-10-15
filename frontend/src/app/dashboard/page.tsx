'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useProjects } from '@/hooks/useApi';
import { Plus, TrendingUp, AlertTriangle, CheckCircle, FileText } from 'lucide-react';
import Link from 'next/link';
import { cn, formatDateTime, getApiErrorMessage } from '@/lib/utils';
import { ErrorState, LoadingState } from '@/components/ui/feedback';

export default function DashboardPage() {
  const { data: projects, isLoading, isError, error, refetch } = useProjects();
  const stats = [
    { label: 'Analyses effectuées', value: projects?.filter(p => p.risk_score !== null).length || 0, icon: CheckCircle, color: 'text-success-500' },
    { label: 'Risques ouverts', value: projects?.reduce((acc, p) => acc + (p.risk_score ? (p.risk_score > 50 ? 1 : 0) : 0), 0) || 0, icon: AlertTriangle, color: 'text-warning-500' },
    { label: 'Score moyen', value: projects && projects.some(p => p.risk_score !== null)
      ? Math.round(projects.filter(p => p.risk_score !== null).reduce((acc, p) => acc + (p.risk_score || 0), 0) / projects.filter(p => p.risk_score !== null).length)
      : 0, icon: TrendingUp, color: 'text-sovereign-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Tableau de bord</h1>
          <p className="page-subtitle">Vue d'ensemble de vos projets de conformité</p>
        </div>
        <Button asChild>
          <Link href="/dashboard/projects">
            <Plus className="h-4 w-4 mr-2" />
            Nouveau projet
          </Link>
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.label}</p>
                  <p className="text-3xl font-bold text-slate-900 mt-1">{stat.value}</p>
                </div>
                <div className={cn('p-3 rounded-xl', stat.color + '/10')}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Projects Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Vos projets</CardTitle>
          <Button asChild variant="ghost" size="sm">
            <Link href="/dashboard/projects">
              <Plus className="h-4 w-4 mr-2" />
              Créer
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingState label="Chargement des projets…" />
          ) : isError ? (
            <ErrorState message={getApiErrorMessage(error, 'Impossible de charger les projets.')} onRetry={() => void refetch()} />
          ) : projects && projects.length > 0 ? (
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
                {projects.map((project) => (
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
                      <Link href={`/dashboard/projects/${project.id}`} className="text-sm text-sovereign-600 hover:underline">
                        Ouvrir
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun projet</h3>
              <p className="text-slate-500 mb-4">Commencez par créer votre premier projet d'audit de conformité.</p>
              <Button asChild>
                <Link href="/dashboard/projects">
                  <Plus className="h-4 w-4 mr-2" />
                  Créer un projet
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
