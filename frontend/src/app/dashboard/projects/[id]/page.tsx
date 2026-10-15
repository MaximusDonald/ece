'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Upload, Settings, FileText, BarChart2, Archive } from 'lucide-react';
import { useProject, useDocuments, useUploadDocument } from '@/hooks/useApi';
import { formatDateTime, formatDate, getApiErrorMessage } from '@/lib/utils';
import { ProjectWorkspaceDocuments } from './components/DocumentsTab';
import { ProjectWorkspaceAnalyses } from './components/AnalysesTab';
import { ProjectWorkspaceReports } from './components/ReportsTab';
import { ProjectWorkspaceSettings } from './components/SettingsTab';
import { ErrorState, LoadingState } from '@/components/ui/feedback';

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading, isError, error, refetch } = useProject(projectId);

  if (isLoading) {
    return (
      <LoadingState label="Chargement du projet…" />
    );
  }

  if (isError) {
    return <ErrorState message={getApiErrorMessage(error, 'Impossible de charger ce projet.')} onRetry={() => void refetch()} />;
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-medium text-slate-900 mb-2">Projet introuvable</h2>
        <Link href="/dashboard/projects">
          <Button variant="secondary">Retour aux projets</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Project Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link href="/dashboard/projects" className="text-sm text-slate-500 hover:underline mb-2 inline-block">
            ← Tous les projets
          </Link>
          <h1 className="page-title">{project.name}</h1>
          <div className="flex items-center gap-3 mt-2">
            <Badge variant={project.country_code.toLowerCase() === 'bj' ? 'default' : 'secondary'}>
              {project.country_code.toUpperCase()}
            </Badge>
            <Badge variant="secondary">{project.sector}</Badge>
            <Badge variant={project.status === 'active' ? 'conforme' : project.status === 'completed' ? 'modere' : 'secondary'}>
              {project.status}
            </Badge>
            {project.treatments.map((t, i) => (
              <Badge key={i} variant="outline" className="text-xs">{t}</Badge>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link href={`/dashboard/projects/${project.id}/upload`}>
              <Upload className="h-4 w-4 mr-2" />
              Téléverser
            </Link>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="documents" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="documents">
            <FileText className="h-4 w-4 mr-2" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="analyses">
            <BarChart2 className="h-4 w-4 mr-2" />
            Analyses
          </TabsTrigger>
          <TabsTrigger value="reports">
            <FileText className="h-4 w-4 mr-2" />
            Rapports
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            Paramètres
          </TabsTrigger>
        </TabsList>

        <TabsContent value="documents">
          <ProjectWorkspaceDocuments projectId={projectId} />
        </TabsContent>
        <TabsContent value="analyses">
          <ProjectWorkspaceAnalyses projectId={projectId} />
        </TabsContent>
        <TabsContent value="reports">
          <ProjectWorkspaceReports projectId={projectId} />
        </TabsContent>
        <TabsContent value="settings">
          <ProjectWorkspaceSettings projectId={projectId} project={project} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
