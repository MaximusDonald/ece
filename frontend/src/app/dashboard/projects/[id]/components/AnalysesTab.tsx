'use client';

import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useDocumentAnalysis, useDocuments } from '@/hooks/useApi';
import { AlertCircle, Brain, CheckCircle, FileText, Loader2 } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

type ProjectDocument = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
};

export function ProjectWorkspaceAnalyses({ projectId }: { projectId: string }) {
  const { data: documents, isLoading, isError } = useDocuments(projectId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analyses des documents</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8" role="status" aria-live="polite">
            <Loader2 className="h-8 w-8 animate-spin text-sovereign-500" />
          </div>
        ) : isError ? (
          <p role="alert" className="py-6 text-center text-danger-700">Impossible de charger les documents à analyser.</p>
        ) : documents?.length ? (
          <div className="space-y-3">
            {documents.map((document) => (
              <AnalysisDocumentRow key={document.id} projectId={projectId} document={document} />
            ))}
          </div>
        ) : (
          <div className="py-10 text-center">
            <Brain className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-800">Aucune analyse</p>
            <p className="mt-1 text-sm text-slate-500">Téléversez un document pour lancer son analyse.</p>
            <Button asChild className="mt-4">
              <Link href={`/dashboard/projects/${projectId}/upload`}>Téléverser un document</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AnalysisDocumentRow({ projectId, document }: { projectId: string; document: ProjectDocument }) {
  const isExtracted = document.status === 'extracted';
  const analysisQuery = useDocumentAnalysis(projectId, document.id, isExtracted);
  const analysisPath = `/dashboard/projects/${projectId}/documents/${document.id}/analysis`;

  let statusContent;
  if (document.status === 'uploaded') {
    statusContent = <Badge variant="secondary"><Loader2 className="mr-1 h-3 w-3 animate-spin" />Téléversé · extraction en cours</Badge>;
  } else if (document.status === 'extracting') {
    statusContent = <Badge variant="a_surveiller"><Loader2 className="mr-1 h-3 w-3 animate-spin" />Extraction en cours</Badge>;
  } else if (document.status === 'extracted' && analysisQuery.data) {
    statusContent = <Badge variant="conforme"><CheckCircle className="mr-1 h-3 w-3" />Analyse terminée</Badge>;
  } else if (document.status === 'extracted' && analysisQuery.isError &&
    (analysisQuery.error as { response?: { status?: number } } | null)?.response?.status !== 404) {
    statusContent = <Badge variant="critique"><AlertCircle className="mr-1 h-3 w-3" />Analyse indisponible</Badge>;
  } else if (document.status === 'extracted') {
    statusContent = <Badge variant="modere"><Loader2 className="mr-1 h-3 w-3 animate-spin" />Analyses en cours</Badge>;
  } else if (document.status === 'failed') {
    statusContent = <Badge variant="critique"><AlertCircle className="mr-1 h-3 w-3" />Échec</Badge>;
  } else {
    statusContent = <Badge variant="secondary">{document.status}</Badge>;
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-center gap-3">
        <FileText className="h-5 w-5 shrink-0 text-slate-400" />
        <div className="min-w-0">
          <p className="truncate font-medium">{document.filename}</p>
          <p className="text-sm text-slate-500">{formatDateTime(document.created_at)}</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 sm:justify-end">
        {statusContent}
        {analysisQuery.data && (
          <Button variant="ghost" size="sm" asChild>
            <Link href={analysisPath}><Brain className="mr-2 h-4 w-4" />Voir l’analyse</Link>
          </Button>
        )}
      </div>
    </div>
  );
}
