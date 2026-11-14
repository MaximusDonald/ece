'use client';

import { useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AlertCircle, ArrowLeft, CheckCircle, FileText, Loader2, ShieldCheck, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useUploadDocument } from '@/hooks/useApi';
import { toast } from '@/hooks/use-toast';
import { formatSize } from '@/lib/utils';

const MAX_SIZE = 50 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.md', '.txt'];
const DOCUMENT_TYPES = [
  ['', 'Détection automatique'],
  ['cahier_charges', 'Cahier des charges'],
  ['privacy_policy', 'Politique de confidentialité'],
  ['contract', 'Contrat'],
  ['terms_conditions', 'Conditions générales'],
  ['internal_procedure', 'Procédure interne'],
  ['compliance_dossier', 'Dossier de conformité'],
  ['technical_specs', 'Spécifications techniques'],
  ['governance', 'Gouvernance des données'],
];

type QueuedFile = {
  id: string;
  file: File;
  documentType: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
};

export default function UploadPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const inputRef = useRef<HTMLInputElement>(null);
  const [queuedFiles, setQueuedFiles] = useState<QueuedFile[]>([]);
  const [defaultDocumentType, setDefaultDocumentType] = useState('');
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isBatchUploading, setIsBatchUploading] = useState(false);
  const upload = useUploadDocument();

  const addFiles = (candidates: FileList | File[] | null) => {
    if (!candidates || candidates.length === 0) return;
    const files = Array.from(candidates);
    const rejected: string[] = [];
    const added: QueuedFile[] = [];

    for (const candidate of files) {
      const lowerName = candidate.name.toLowerCase();
      if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
        rejected.push(`${candidate.name} (format non pris en charge)`);
        continue;
      }
      if (candidate.size > MAX_SIZE) {
        rejected.push(`${candidate.name} (> 50 Mo)`);
        continue;
      }
      const exists = queuedFiles.some(
        (q) => q.file.name === candidate.name && q.file.size === candidate.size && q.status !== 'done',
      );
      if (!exists) {
        added.push({
          id: `${candidate.name}-${candidate.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          file: candidate,
          documentType: defaultDocumentType,
          status: 'pending',
        });
      }
    }

    if (rejected.length > 0) {
      setError(`Fichier(s) ignoré(s) : ${rejected.join(', ')}. Formats acceptés : PDF, DOCX, Markdown, TXT (50 Mo max).`);
    } else {
      setError('');
    }

    if (added.length > 0) {
      setQueuedFiles((prev) => [...prev, ...added]);
    }
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  const startAnalysis = async () => {
    const itemsToUpload = queuedFiles.filter((q) => q.status === 'pending' || q.status === 'error');
    if (itemsToUpload.length === 0) return;

    setError('');
    setIsBatchUploading(true);
    const uploadedDocs: { id: string }[] = [];
    let errorCount = 0;

    const BATCH_SIZE = 3;
    for (let i = 0; i < itemsToUpload.length; i += BATCH_SIZE) {
      const batch = itemsToUpload.slice(i, i + BATCH_SIZE);
      await Promise.all(
        batch.map(async (item) => {
          setQueuedFiles((prev) =>
            prev.map((q) => (q.id === item.id ? { ...q, status: 'uploading', error: undefined } : q)),
          );
          try {
            const doc = await upload.mutateAsync({
              projectId,
              file: item.file,
              documentType: item.documentType || undefined,
            });
            uploadedDocs.push(doc);
            setQueuedFiles((prev) =>
              prev.map((q) => (q.id === item.id ? { ...q, status: 'done' } : q)),
            );
          } catch (cause) {
            errorCount += 1;
            const apiError = cause as { response?: { data?: { detail?: string } } };
            const msg = apiError.response?.data?.detail || 'Le dépôt a échoué.';
            setQueuedFiles((prev) =>
              prev.map((q) => (q.id === item.id ? { ...q, status: 'error', error: msg } : q)),
            );
          }
        }),
      );
    }

    setIsBatchUploading(false);

    if (errorCount === 0 && uploadedDocs.length === 1 && queuedFiles.length === 1) {
      router.push(`/dashboard/projects/${projectId}/documents/${uploadedDocs[0].id}/pipeline`);
      return;
    }

    if (errorCount === 0 && uploadedDocs.length > 0) {
      toast({
        title: `${uploadedDocs.length} documents déposés avec succès`,
        description: 'Les pipelines d’extraction et d’analyse juridique ont démarré en parallèle.',
      });
      router.push(`/dashboard/projects/${projectId}`);
      return;
    }

    if (uploadedDocs.length > 0 && errorCount > 0) {
      setError(`${uploadedDocs.length} document(s) déposé(s), mais ${errorCount} ont échoué. Vous pouvez réessayer ou retirer les fichiers en erreur.`);
    } else if (errorCount > 0) {
      setError('Le dépôt a échoué. Vérifiez votre connexion ou les formats de fichiers puis réessayez.');
    }
  };

  const pendingCount = queuedFiles.filter((q) => q.status === 'pending' || q.status === 'error').length;

  return (
    <main className="mx-auto max-w-4xl space-y-7 pb-10">
      <div>
        <Link href={`/dashboard/projects/${projectId}`} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" /> Retour au projet
        </Link>
        <p className="text-sm font-semibold uppercase tracking-wider text-sovereign-600">Audit documentaire</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Déposez vos documents</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Sélectionnez un ou plusieurs documents en une fois. Nous allons extraire leur contenu, les comparer au corpus juridique et générer votre rapport consolidé.
        </p>
      </div>

      <Card className="overflow-hidden border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-100 bg-slate-50/70">
          <CardTitle className="text-lg">Documents à analyser</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 p-6 sm:p-8">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); if (!isBatchUploading) setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragging(false);
              if (!isBatchUploading) addFiles(event.dataTransfer.files);
            }}
            disabled={isBatchUploading}
            className={`flex min-h-48 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${isDragging ? 'border-sovereign-500 bg-sovereign-50' : 'border-slate-300 bg-white hover:border-sovereign-400 hover:bg-slate-50'}`}
            aria-label="Choisir ou déposer un ou plusieurs documents à analyser"
          >
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.md,.txt"
              className="sr-only"
              onChange={(event) => addFiles(event.target.files)}
              disabled={isBatchUploading}
            />
            <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sovereign-50 text-sovereign-700">
              <Upload className="h-7 w-7" />
            </span>
            <span className="font-semibold text-slate-900">Glissez vos fichiers ici</span>
            <span className="mt-1 text-sm text-slate-500">ou cliquez pour sélectionner plusieurs fichiers sur votre ordinateur</span>
            <span className="mt-4 text-xs text-slate-400">PDF · DOCX · Markdown · TXT · 50 Mo maximum par fichier</span>
          </button>

          {queuedFiles.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-800">
                  {queuedFiles.length} document{queuedFiles.length > 1 ? 's' : ''} prêt{queuedFiles.length > 1 ? 's' : ''} à être déposé{queuedFiles.length > 1 ? 's' : ''}
                </span>
                {!isBatchUploading && (
                  <button
                    type="button"
                    onClick={() => { setQueuedFiles([]); setError(''); if (inputRef.current) inputRef.current.value = ''; }}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-danger-600"
                  >
                    <X className="h-3.5 w-3.5" /> Tout retirer
                  </button>
                )}
              </div>

              <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                {queuedFiles.map((item) => (
                  <div
                    key={item.id}
                    className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border text-sm ${
                      item.status === 'done'
                        ? 'bg-emerald-50/70 border-emerald-200'
                        : item.status === 'error'
                        ? 'bg-danger-50 border-danger-200'
                        : 'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {item.status === 'uploading' && <Loader2 className="h-5 w-5 shrink-0 animate-spin text-sovereign-600" />}
                      {item.status === 'done' && <CheckCircle className="h-5 w-5 shrink-0 text-emerald-600" />}
                      {item.status === 'error' && <AlertCircle className="h-5 w-5 shrink-0 text-danger-600" />}
                      {item.status === 'pending' && <FileText className="h-5 w-5 shrink-0 text-slate-400" />}
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-slate-900 truncate">{item.file.name}</p>
                        <p className="text-xs text-slate-500">
                          {formatSize(item.file.size)}
                          {item.error && <span className="text-danger-600 ml-2">· {item.error}</span>}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        value={item.documentType}
                        onChange={(e) => {
                          const val = e.target.value;
                          setQueuedFiles((prev) =>
                            prev.map((q) => (q.id === item.id ? { ...q, documentType: val } : q)),
                          );
                        }}
                        disabled={isBatchUploading || item.status === 'done'}
                        className="text-xs border border-slate-300 rounded-md px-2 py-1.5 bg-white"
                        aria-label={`Nature pour ${item.file.name}`}
                      >
                        {DOCUMENT_TYPES.map(([value, label]) => (
                          <option key={value || 'auto'} value={value}>{label}</option>
                        ))}
                      </select>
                      {!isBatchUploading && item.status !== 'done' && (
                        <button
                          type="button"
                          onClick={() => setQueuedFiles((prev) => prev.filter((q) => q.id !== item.id))}
                          className="p-1 text-slate-400 hover:text-danger-600"
                          aria-label={`Retirer ${item.file.name}`}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="document-type">Nature par défaut des documents <span className="font-normal text-slate-400">(facultatif)</span></Label>
            <select
              id="document-type"
              value={defaultDocumentType}
              onChange={(event) => {
                const val = event.target.value;
                setDefaultDocumentType(val);
                setQueuedFiles((prev) =>
                  prev.map((q) => (q.status === 'pending' ? { ...q, documentType: val } : q)),
                );
              }}
              className="input w-full"
              disabled={isBatchUploading}
            >
              {DOCUMENT_TYPES.map(([value, label]) => <option key={value || 'auto'} value={value}>{label}</option>)}
            </select>
            <p className="text-xs text-slate-500">Cela aide l’audit à interpréter les clauses dans leur contexte (modifiable individuellement ci-dessus).</p>
          </div>

          {error && (
            <div role="alert" className="flex gap-3 rounded-lg border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span>
            </div>
          )}

          <div className="flex flex-col gap-4 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="flex items-center gap-2 text-xs text-slate-500"><ShieldCheck className="h-4 w-4 text-success-600" />Les documents restent isolés dans l’espace de votre organisation.</p>
            <Button onClick={startAnalysis} disabled={pendingCount === 0 || isBatchUploading} className="min-w-52">
              {isBatchUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Dépôt ({queuedFiles.filter((q) => q.status === 'done').length}/{queuedFiles.length})…
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Déposer et analyser {pendingCount > 1 ? `(${pendingCount} documents)` : ''}
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ['1', 'Extraction', 'Texte et structure des documents'],
          ['2', 'Audit de conformité', 'Analyse croisée et recherche juridique'],
          ['3', 'Rapport unifié', 'Constats, risques, articles et recommandations'],
        ].map(([number, title, description]) => (
          <div key={number} className="flex gap-3 rounded-lg border border-slate-200 bg-white p-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600">{number}</span>
            <div><p className="text-sm font-medium text-slate-800">{title}</p><p className="mt-1 text-xs text-slate-500">{description}</p></div>
          </div>
        ))}
      </div>
    </main>
  );
}
