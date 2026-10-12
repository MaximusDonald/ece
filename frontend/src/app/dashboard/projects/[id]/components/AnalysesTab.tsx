'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useDocuments, useJobStatus } from '@/hooks/useApi';
import { Clock, CheckCircle, AlertCircle, Search, Brain, Scale, FileText, TrendingUp } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { useState, useEffect } from 'react';

const ANALYSIS_STEPS = [
  { step: 1, name: 'Extraction', icon: FileText },
  { step: 2, name: 'Analyse sémantique', icon: Brain },
  { step: 3, name: 'Recherche juridique', icon: Scale },
  { step: 4, name: 'Scoring', icon: TrendingUp },
  { step: 5, name: 'Génération rapport', icon: FileText },
];

export function ProjectWorkspaceAnalyses({ projectId }: { projectId: string }) {
  const { data: documents, isLoading } = useDocuments(projectId);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);

  // Find the latest processing document
  const processingDoc = documents?.find(d => d.status === 'processing' || d.status === 'extracting');
  const latestCompletedDoc = documents?.filter(d => d.status === 'completed').sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )[0];

  // Auto-select the processing job
  useEffect(() => {
    if (processingDoc) {
      // We'd need to track job ID - for now, we'll show the stepper for the latest doc
    }
  }, [processingDoc]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-success-500" />;
      case 'processing': return <Clock className="h-5 w-5 text-sovereign-500 animate-spin" />;
      case 'failed': return <AlertCircle className="h-5 w-5 text-danger-500" />;
      default: return <Clock className="h-5 w-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Current Analysis */}
      {processingDoc && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Analyse en cours</CardTitle>
            <Badge variant="modere">Traitement</Badge>
          </CardHeader>
          <CardContent>
            <div className="mb-6">
              <p className="text-sm text-slate-600 mb-2">Document : {processingDoc.filename}</p>
              <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-sovereign-500 rounded-full transition-all duration-300" style={{ width: '45%' }} />
              </div>
              <p className="text-xs text-slate-500 mt-1">Environ 2 minutes restantes</p>
            </div>

            {/* Stepper */}
            <div className="flex items-start gap-4 overflow-x-auto pb-4">
              {ANALYSIS_STEPS.map((step, index) => (
                <div key={step.step} className="flex flex-col items-center flex-shrink-0 stepper-step">
                  <div className={cn(
                    'stepper-circle',
                    index < 2 && 'stepper-step-completed',
                    index === 2 && 'stepper-step-active'
                  )}>
                    {index < 2 ? <CheckCircle className="h-4 w-4" /> : step.step}
                  </div>
                  <span className="stepper-label">{step.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Analyses */}
      <Card>
        <CardHeader>
          <CardTitle>Analyses récentes</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : documents && documents.length > 0 ? (
            <div className="space-y-4">
              {documents
                .filter(d => d.status === 'completed' || d.status === 'failed')
                .slice(0, 5)
                .map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                    <div className="flex items-center gap-4">
                      <FileText className="h-6 w-6 text-slate-400" />
                      <div>
                        <p className="font-medium">{doc.filename}</p>
                        <p className="text-sm text-slate-500">{formatDateTime(doc.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={doc.status === 'completed' ? 'conforme' : 'critique'}>
                        {doc.status === 'completed' ? 'Terminé' : 'Échoué'}
                      </Badge>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/dashboard/projects/${projectId}/documents/${doc.id}/extraction`}>
                          <FileText className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/dashboard/projects/${projectId}/documents/${doc.id}/analysis`}>
                          <Brain className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Brain className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucune analyse</h3>
              <p className="text-slate-500 mb-4">Téléversez un document pour lancer l'analyse automatique.</p>
              <Button asChild>
                <Link href={`/dashboard/projects/${projectId}/upload`}>
                  <Upload className="h-4 w-4 mr-2" />
                  Téléverser un document
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analysis Pipeline Info */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline d'analyse</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-5">
            {ANALYSIS_STEPS.map((step) => (
              <div key={step.step} className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="w-12 h-12 rounded-full bg-sovereign-100 flex items-center justify-center mx-auto mb-3">
                  <step.icon className="h-6 w-6 text-sovereign-600" />
                </div>
                <p className="font-medium text-sm">{step.name}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {step.step === 1 && 'PyMuPDF / python-docx'}
                  {step.step === 2 && 'spaCy NER + LLM'}
                  {step.step === 3 && 'PGVector + LLM RAG'}
                  {step.step === 4 && 'Règles déterministes'}
                  {step.step === 5 && 'WeasyPrint PDF'}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Upload } from 'lucide-react';