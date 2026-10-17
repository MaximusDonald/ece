'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { AlertCircle, ArrowLeft, Check, CheckCircle2, Circle, FileText, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useDocumentPipeline } from '@/hooks/useApi';
import { formatDateTime } from '@/lib/utils';

const STEP_GUIDANCE: Record<string, string> = {
  extraction: 'Le texte et la structure sont lus. Les fichiers scannés sans texte exploitable peuvent demander une reprise.',
  semantic: 'Le contenu est parcouru pour repérer les sujets, les clauses et les informations qui manquent.',
  legal_research: 'Les constats sont rapprochés du corpus interne correspondant au pays et au périmètre du projet.',
  scoring: 'Les niveaux de risque et de confiance sont calculés à partir des constats et des règles applicables.',
  report: 'Les deux rapports sont assemblés. Les versions web et PDF sont préparées.',
};

export default function DocumentPipelinePage() {
  const params = useParams();
  const projectId = params.id as string;
  const documentId = params.documentId as string;
  const { data: pipeline, isLoading, isError, refetch, resume } = useDocumentPipeline(projectId, documentId);
  const isTerminal = pipeline?.status === 'completed' || pipeline?.status === 'failed';

  if (isLoading) {
    return <div className="mx-auto flex max-w-3xl flex-col items-center py-24 text-center"><Loader2 className="h-8 w-8 animate-spin text-sovereign-600" /><p className="mt-4 font-medium text-slate-800">Préparation du suivi</p><p className="mt-1 text-sm text-slate-500">Nous récupérons l’état de votre audit.</p></div>;
  }

  if (isError || !pipeline) {
    return (
      <main className="mx-auto max-w-3xl py-12">
        <Card><CardContent className="flex flex-col items-center p-8 text-center">
          <AlertCircle className="h-10 w-10 text-danger-600" />
          <h1 className="mt-4 text-xl font-semibold text-slate-900">Suivi momentanément indisponible</h1>
          <p className="mt-2 max-w-lg text-sm text-slate-600">Le document a peut-être bien été déposé. Réessayez de charger le suivi avant de le déposer à nouveau.</p>
          <Button className="mt-5" variant="outline" onClick={() => refetch()}><RefreshCw className="mr-2 h-4 w-4" />Réessayer</Button>
        </CardContent></Card>
      </main>
    );
  }

  const currentStep = pipeline.steps.find((step) => step.step === pipeline.current_step);
  const statusLabel = pipeline.status === 'completed' ? 'Rapports prêts' : pipeline.status === 'failed' ? 'Action nécessaire' : pipeline.status === 'queued' ? 'Dans la file de traitement' : 'Analyse en cours';

  return (
    <main className="mx-auto max-w-5xl space-y-6 pb-12">
      <Link href={`/dashboard/projects/${projectId}`} className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="h-4 w-4" />Retour au projet</Link>

      <Card className="overflow-hidden border-slate-200 shadow-sm">
        <div className="bg-gradient-to-r from-slate-950 to-sovereign-900 px-6 py-7 text-white sm:px-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/10"><FileText className="h-6 w-6" /></span>
              <div className="min-w-0">
                <p className="text-sm text-blue-100">Audit documentaire</p>
                <h1 className="mt-1 break-all text-xl font-semibold">{pipeline.filename || 'Votre document'}</h1>
                <p className="mt-2 text-sm text-blue-100">{isTerminal ? statusLabel : currentStep?.message || 'Votre document a bien été reçu.'}</p>
              </div>
            </div>
            <Badge variant={pipeline.status === 'completed' ? 'conforme' : pipeline.status === 'failed' ? 'critique' : 'modere'} className="w-fit shrink-0">{statusLabel}</Badge>
          </div>
          <div className="mt-7">
            <div className="mb-2 flex justify-between text-xs text-blue-100"><span>Progression de l’audit</span><span>{pipeline.progress}%</span></div>
            <Progress value={pipeline.progress} className="h-2 bg-white/20 [&>div]:bg-emerald-300" />
          </div>
        </div>
        <CardContent className="grid gap-4 p-5 sm:grid-cols-3 sm:p-6">
          <div><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Étape actuelle</p><p className="mt-1 font-medium text-slate-800">{currentStep?.label || (pipeline.status === 'completed' ? 'Toutes les étapes terminées' : '—')}</p></div>
          <div><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Dernière mise à jour</p><p className="mt-1 font-medium text-slate-800">{pipeline.updated_at ? formatDateTime(pipeline.updated_at) : 'À l’instant'}</p></div>
          <div><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Confidentialité</p><p className="mt-1 flex items-center gap-2 font-medium text-slate-800"><ShieldCheck className="h-4 w-4 text-success-600" />Espace isolé de votre organisation</p></div>
        </CardContent>
      </Card>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(260px,0.8fr)]">
        <Card>
          <CardHeader><CardTitle>Les étapes de votre audit</CardTitle><p className="text-sm text-slate-500">Les résultats apparaissent au fur et à mesure. Vous pouvez quitter cette page : le traitement continue en arrière-plan.</p></CardHeader>
          <CardContent>
            <ol className="space-y-1">
              {pipeline.steps.map((step, index) => {
                const active = step.status === 'running' || step.status === 'retrying';
                const done = step.status === 'completed';
                const failed = step.status === 'failed';
                return (
                  <li key={step.step} className="relative flex gap-4 pb-6 last:pb-0">
                    {index < pipeline.steps.length - 1 && <span className={`absolute left-[15px] top-8 h-[calc(100%-12px)] w-px ${done ? 'bg-emerald-300' : 'bg-slate-200'}`} aria-hidden="true" />}
                    <span className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${done ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : active ? 'border-sovereign-200 bg-sovereign-50 text-sovereign-700' : failed ? 'border-danger-200 bg-danger-50 text-danger-700' : 'border-slate-200 bg-white text-slate-400'}`}>
                      {done ? <Check className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : failed ? <AlertCircle className="h-4 w-4" /> : <Circle className="h-3 w-3" />}
                    </span>
                    <div className="min-w-0 flex-1 pt-0.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className={`font-medium ${active ? 'text-sovereign-800' : done ? 'text-slate-900' : failed ? 'text-danger-800' : 'text-slate-500'}`}>{step.label}</p>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${done ? 'bg-emerald-50 text-emerald-700' : active ? 'bg-sovereign-50 text-sovereign-700' : failed ? 'bg-danger-50 text-danger-700' : 'bg-slate-100 text-slate-500'}`}>{done ? 'Terminé' : step.status === 'retrying' ? 'Nouvelle tentative' : active ? 'En cours' : failed ? 'Échec' : 'À venir'}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-500">{step.message}. {STEP_GUIDANCE[step.key]}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {pipeline.status === 'failed' ? (
            <Card className="border-danger-200 bg-danger-50/60">
              <CardHeader><CardTitle className="flex items-center gap-2 text-danger-800"><AlertCircle className="h-5 w-5" />Une étape a échoué</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-danger-800">{pipeline.error || 'Le traitement s’est interrompu. Vos fichiers déposés restent disponibles.'}</p>
                <Button className="mt-4 w-full" onClick={() => resume.mutate({ projectId, documentId })} disabled={resume.isPending}>
                  {resume.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Reprise…</> : <><RefreshCw className="mr-2 h-4 w-4" />Relancer cette étape</>}
                </Button>
                {resume.isError && <p role="alert" className="mt-3 text-xs text-danger-700">La reprise n’a pas pu être lancée. Vérifiez que le serveur et le worker sont démarrés, puis réessayez.</p>}
              </CardContent>
            </Card>
          ) : pipeline.status === 'completed' ? (
            <Card className="border-emerald-200 bg-emerald-50/60">
              <CardHeader><CardTitle className="flex items-center gap-2 text-emerald-900"><CheckCircle2 className="h-5 w-5" />Votre audit est prêt</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-emerald-900">Les constats, les niveaux de risque et les recommandations sont disponibles dans le rapport du projet.</p>
                {pipeline.warnings.map((warning) => <p key={warning} className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-800">{warning}</p>)}
                <Button asChild className="mt-4 w-full"><Link href={pipeline.report_version_id ? `/dashboard/projects/${projectId}/reports/${pipeline.report_version_id}` : `/dashboard/projects/${projectId}?tab=reports`}>Consulter le rapport</Link></Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-slate-50">
              <CardHeader><CardTitle className="text-base">Que se passe-t-il ?</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-600">
                <p>Chaque étape enregistre son résultat avant de démarrer la suivante. Le suivi se met à jour automatiquement.</p>
                <p>La recherche s’appuie sur le corpus interne du projet. Si une information est insuffisante, le rapport la signalera avec son niveau de confiance.</p>
                <p className="rounded-md border border-slate-200 bg-white p-3 text-xs">Vous pouvez fermer cette page et revenir depuis l’onglet <strong>Analyses</strong> du projet.</p>
              </CardContent>
            </Card>
          )}
          <Button variant="outline" asChild className="w-full"><Link href={`/dashboard/projects/${projectId}`}>Retour à l’espace projet</Link></Button>
        </div>
      </div>
    </main>
  );
}
