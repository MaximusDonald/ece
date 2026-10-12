'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useDocumentExtraction } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileText, Download, ChevronLeft, Copy, Check } from 'lucide-react';
import { formatDateTime, formatSize } from '@/lib/utils';
import { useState } from 'react';

export default function ExtractionPage() {
  const params = useParams();
  const projectId = params.id as string;
  const documentId = params.documentId as string;
  const { data: extraction, isLoading, refetch } = useDocumentExtraction(projectId, documentId);
  const [copied, setCopied] = useState(false);

  const copyMarkdown = async () => {
    if (!extraction) return;
    await navigator.clipboard.writeText(extraction.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
      </div>
    );
  }

  if (!extraction) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900 mb-2">Extraction non trouvée</h3>
        <Link href={`/dashboard/projects/${projectId}`}>
          <Button variant="secondary">Retour au projet</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/projects/${projectId}`} className="text-sm text-slate-500 hover:underline flex items-center gap-1">
            <ChevronLeft className="h-4 w-4" />
            Projet
          </Link>
          <div>
            <h1 className="page-title">Extraction du document</h1>
            <p className="page-subtitle">Contenu structuré en Markdown</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={copyMarkdown}>
            {copied ? (
              <>
                <Check className="h-4 w-4 mr-2 text-success-500" />
                Copié !
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Copier le Markdown
              </>
            )}
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/api/documents/${extraction.document_id}/download`} target="_blank">
              <Download className="h-4 w-4 mr-2" />
              Télécharger
            </Link>
          </Button>
        </div>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Métadonnées d'extraction</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Qualité d'extraction</p>
              <p className="text-2xl font-bold text-slate-900">
                {(extraction.quality_score * 100).toFixed(0)}%
              </p>
              <Badge variant={extraction.quality_score > 0.8 ? 'conforme' : extraction.quality_score > 0.5 ? 'modere' : 'critique'} className="mt-1">
                {extraction.quality_score > 0.8 ? 'Excellente' : extraction.quality_score > 0.5 ? 'Correcte' : 'Faible'}
              </Badge>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Pages détectées</p>
              <p className="text-2xl font-bold text-slate-900">{extraction.page_count}</p>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Langue</p>
              <p className="text-2xl font-bold text-slate-900 capitalize">{extraction.language}</p>
            </div>
            <div className="p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Date d'extraction</p>
              <p className="font-medium text-slate-900">{formatDateTime(extraction.created_at)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Markdown Content */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Contenu Markdown extrait</CardTitle>
          <Badge variant="outline">{extraction.markdown.length} caractères</Badge>
        </CardHeader>
        <CardContent>
          <div className="border border-slate-200 rounded-lg bg-slate-50 max-h-[600px] overflow-auto p-4 font-mono text-sm">
            <pre className="whitespace-pre-wrap text-slate-800">{extraction.markdown || 'Aucun contenu extrait'}</pre>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="secondary" asChild>
          <Link href={`/dashboard/projects/${projectId}`}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            Retour au projet
          </Link>
        </Button>
        <Button asChild>
          <Link href={`/dashboard/projects/${projectId}/documents/${documentId}/analysis`}>
            Voir l'analyse sémantique
          </Link>
        </Button>
      </div>
    </div>
  );
}