'use client';

import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useUploadDocument, useJobStatus } from '@/hooks/useApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Upload, FileText, Loader2, CheckCircle, X, AlertCircle, ChevronLeft } from 'lucide-react';
import Link from 'next/link';
import { toast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/markdown',
  'text/plain',
];

const MAX_SIZE = 50 * 1024 * 1024; // 50 MB

const STEPS = [
  { step: 1, name: 'Extraction', desc: 'Extraction du texte et structure' },
  { step: 2, name: 'Analyse sémantique', desc: 'Détection entités, clauses, zones floues' },
  { step: 3, name: 'Recherche juridique', desc: 'RAG sur corpus CEDEAO/UEMOA/Bénin' },
  { step: 4, name: 'Scoring', desc: 'Évaluation risques + badges confiance' },
  { step: 5, name: 'Génération rapport', desc: 'Double rapport + PDF' },
];

export default function UploadPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const searchParams = useSearchParams();
  const jobIdParam = searchParams.get('jobId');

  const [isUploadOpen, setIsUploadOpen] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useUploadDocument();
  const { data: jobStatus, refetch } = useJobStatus(projectId, jobIdParam as any, !!jobIdParam);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!ALLOWED_TYPES.includes(file.type)) {
        setError('Type de fichier non autorisé. Formats acceptés : PDF, DOCX, Markdown, Texte');
        return;
      }
      if (file.size > MAX_SIZE) {
        setError('Fichier trop volumineux. Taille maximale : 50 Mo');
        return;
      }
      setError(null);
      setUploadFile(file);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setError(null);
    try {
      const result = await uploadMutation.mutateAsync({
        projectId,
        file: uploadFile,
        documentType: documentType || undefined,
      });
      // Redirect to analysis page with job ID
      router.push(`/dashboard/projects/${projectId}/analysis/${result.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du téléversement');
    }
  };

  // If we have a jobId, we're in progress mode
  if (jobIdParam) {
    return <AnalysisProgressPage projectId={projectId} jobId={jobIdParam} />;
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <Badge variant="conforme"><CheckCircle className="h-3 w-3 mr-1" />Terminé</Badge>;
      case 'processing': return <Badge variant="modere"><Loader2 className="h-3 w-3 mr-1 animate-spin" />En cours</Badge>;
      case 'extracting': return <Badge variant="a_surveiller"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Extraction</Badge>;
      case 'failed': return <Badge variant="critique"><AlertCircle className="h-3 w-3 mr-1" />Échoué</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/projects/${projectId}`} className="text-sm text-slate-500 hover:underline flex items-center gap-1">
            <ChevronLeft className="h-4 w-4" />
            Retour au projet
          </Link>
          <div>
            <h1 className="page-title">Téléverser un document</h1>
            <p className="page-subtitle">PDF, DOCX, Markdown ou Texte (max 50 Mo)</p>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Nouveau document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-danger-700 text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {/* File Drop Zone */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-sovereign-400 transition-colors">
            <input
              type="file"
              accept=".pdf,.docx,.md,.txt"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
              disabled={uploadMutation.isPending}
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              {uploadFile ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-3 p-4 bg-sovereign-50 border border-sovereign-200 rounded-lg">
                    <FileText className="h-10 w-10 text-sovereign-600" />
                    <div className="text-left">
                      <p className="font-medium text-sovereign-700">{uploadFile.name}</p>
                      <p className="text-sm text-sovereign-600">{(uploadFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <button
                      onClick={(e) => { e.preventDefault(); setUploadFile(null); setError(null); }}
                      className="ml-4 text-slate-400 hover:text-slate-600"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                  <p className="text-sm text-slate-500">Cliquez pour changer de fichier</p>
                </div>
              ) : (
                <>
                  <Upload className="h-14 w-14 text-slate-300 mx-auto mb-4" />
                  <p className="text-lg text-slate-600 mb-1">Cliquez ou glissez-déposez un fichier</p>
                  <p className="text-sm text-slate-400">PDF, DOCX, Markdown, Texte (max 50 Mo)</p>
                </>
              )}
            </label>
          </div>

          {/* Document Type */}
          <div>
            <Label htmlFor="document_type">Type de document (optionnel)</Label>
            <select
              id="document_type"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="input mt-1"
            >
              <option value="">Détection automatique</option>
              <option value="cahier_charges">Cahier des charges</option>
              <option value="privacy_policy">Politique de confidentialité</option>
              <option value="contract">Contrat</option>
              <option value="terms_conditions">Conditions générales</option>
              <option value="internal_procedure">Procédure interne</option>
              <option value="compliance_dossier">Dossier de conformité</option>
              <option value="technical_specs">Spécifications techniques</option>
              <option value="governance">Gouvernance des données</option>
            </select>
          </div>

          {/* Upload Button */}
          <div className="flex justify-end pt-4 border-t border-slate-200">
            <Button
              onClick={handleUpload}
              disabled={!uploadFile || uploadMutation.isPending}
              className="w-full sm:w-auto"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Téléversement...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Téléverser et lancer l'analyse
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Pipeline Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline d'analyse (5 étapes)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            {STEPS.map((step, index) => (
              <div key={step.step} className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
                <div className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0',
                  index === 0 ? 'bg-sovereign-100 text-sovereign-600' : 'bg-slate-200 text-slate-400'
                )}>
                  {step.step}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-slate-900">{step.name}</p>
                  <p className="text-sm text-slate-500">{step.desc}</p>
                </div>
                <Badge variant="outline" className="text-xs">Étape {step.step}/5</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AnalysisProgressPage({ projectId, jobId }: { projectId: string; jobId: string }) {
  const router = useRouter();
  const { data: jobStatus, refetch } = useJobStatus(projectId, jobId as any, true);

  const getStepStatus = (stepNum: number) => {
    if (!jobStatus) return 'pending';
    if (jobStatus.status === 'completed' || jobStatus.status === 'failed') return 'completed';
    // For simplicity, assume sequential - in reality would parse from job info
    const currentStep = jobStatus.steps.find(s => s.status === 'processing')?.step || 1;
    if (stepNum < currentStep) return 'completed';
    if (stepNum === currentStep) return 'processing';
    return 'pending';
  };

  if (!jobStatus) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-sovereign-500" />
        <p className="mt-4 text-slate-600">Chargement du statut...</p>
      </div>
    );
  }

  const isTerminal = jobStatus.status === 'completed' || jobStatus.status === 'failed';

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
            <h1 className="page-title">Analyse en cours</h1>
            <p className="page-subtitle">
              {isTerminal 
                ? (jobStatus.status === 'completed' ? 'Analyse terminée avec succès' : 'Échec de l\'analyse')
                : 'Traitement asynchrone en cours...'}
            </p>
          </div>
        </div>
        {isTerminal && (
          <Button 
            variant={jobStatus.status === 'completed' ? 'default' : 'outline'} 
            asChild
            onClick={() => router.push(`/dashboard/projects/${projectId}/reports/${jobStatus.result?.report_version_id || ''}`)}
          >
            {jobStatus.status === 'completed' ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Voir le rapport
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 mr-2" />
                Réessayer
              </>
            )}
          </Button>
        )}
      </div>

      {/* Progress Stepper */}
      <Card>
        <CardHeader>
          <CardTitle>Progression des 5 étapes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            {STEPS.map((step, index) => {
              const status = getStepStatus(step.step);
              return (
                <div key={step.step} className={cn('flex items-start gap-4', status === 'processing' && 'animate-pulse')}>
                  <div className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0',
                    status === 'completed' && 'bg-success-100 text-success-600',
                    status === 'processing' && 'bg-sovereign-100 text-sovereign-600 animate-pulse',
                    status === 'pending' && 'bg-slate-200 text-slate-400'
                  )}>
                    {status === 'completed' ? <CheckCircle className="h-5 w-5" /> : step.step}
                  </div>
                  <div className="flex-1 pt-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('font-medium', status === 'processing' && 'text-sovereign-600')}>
                        {step.name}
                      </span>
                      <Badge variant={
                        status === 'completed' ? 'conforme' :
                        status === 'processing' ? 'modere' : 'secondary'
                      } className="text-xs">
                        {status === 'completed' ? 'Terminé' : status === 'processing' ? 'En cours' : 'En attente'}
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-500">{step.desc}</p>
                    <Progress value={status === 'completed' ? 100 : status === 'processing' ? 50 : 0} className="mt-2 h-1.5" />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Status Info */}
      <Card>
        <CardHeader>
          <CardTitle>Détails</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-3 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Statut global</p>
              <p className="font-medium capitalize">{jobStatus.status}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">ID de tâche</p>
              <p className="font-mono text-sm">{jobId.slice(0, 12)}...</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-500">Temps estimé restant</p>
              <p className="font-medium">{jobStatus.estimated_remaining_seconds ? `${Math.ceil(jobStatus.estimated_remaining_seconds / 60)} min` : '—'}</p>
            </div>
          </div>

          {jobStatus.error && (
            <div className="p-4 bg-danger-50 border border-danger-200 rounded-lg text-danger-700">
              <p className="font-medium mb-1">Erreur :</p>
              <p className="text-sm">{jobStatus.error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {isTerminal && jobStatus.status === 'completed' && (
        <Card className="border-success-200 bg-success-50">
          <CardContent className="p-6 text-center">
            <CheckCircle className="h-12 w-12 text-success-500 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-success-700 mb-2">Analyse terminée !</h3>
            <p className="text-slate-600 mb-4">Le double rapport est prêt. Vous pouvez le consulter ou ajouter du contexte complémentaire.</p>
            <Button asChild size="lg">
              <Link href={`/dashboard/projects/${projectId}/reports/${jobStatus.result?.report_version_id || ''}`}>
                Voir le rapport complet
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}