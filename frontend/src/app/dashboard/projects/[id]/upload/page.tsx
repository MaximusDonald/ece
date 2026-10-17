'use client';

import { useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AlertCircle, ArrowLeft, FileText, Loader2, ShieldCheck, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useUploadDocument } from '@/hooks/useApi';
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

export default function UploadPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const upload = useUploadDocument();

  const chooseFile = (candidate?: File) => {
    if (!candidate) return;
    const lowerName = candidate.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
      setError('Ce format ne peut pas être analysé. Choisissez un PDF, un DOCX, un fichier Markdown ou texte.');
      return;
    }
    if (candidate.size > MAX_SIZE) {
      setError('Le fichier dépasse la limite de 50 Mo.');
      return;
    }
    setError('');
    setFile(candidate);
  };

  const startAnalysis = async () => {
    if (!file) return;
    setError('');
    try {
      const document = await upload.mutateAsync({
        projectId,
        file,
        documentType: documentType || undefined,
      });
      router.push(`/dashboard/projects/${projectId}/documents/${document.id}/pipeline`);
    } catch (cause) {
      const apiError = cause as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail || 'Le dépôt a échoué. Vérifiez votre connexion puis réessayez.');
    }
  };

  return (
    <main className="mx-auto max-w-4xl space-y-7 pb-10">
      <div>
        <Link href={`/dashboard/projects/${projectId}`} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900">
          <ArrowLeft className="h-4 w-4" /> Retour au projet
        </Link>
        <p className="text-sm font-semibold uppercase tracking-wider text-sovereign-600">Audit documentaire</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Déposez votre document</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Nous allons extraire son contenu, le comparer au corpus juridique du projet et préparer deux rapports traçables.
        </p>
      </div>

      <Card className="overflow-hidden border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-100 bg-slate-50/70">
          <CardTitle className="text-lg">Document à analyser</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 p-6 sm:p-8">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(event) => { event.preventDefault(); setIsDragging(false); chooseFile(event.dataTransfer.files[0]); }}
            className={`flex min-h-64 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${isDragging ? 'border-sovereign-500 bg-sovereign-50' : 'border-slate-300 bg-white hover:border-sovereign-400 hover:bg-slate-50'}`}
            aria-label="Choisir ou déposer un document à analyser"
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.md,.txt"
              className="sr-only"
              onChange={(event) => chooseFile(event.target.files?.[0])}
              disabled={upload.isPending}
            />
            {file ? (
              <>
                <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sovereign-50 text-sovereign-700"><FileText className="h-7 w-7" /></span>
                <span className="max-w-full break-all font-medium text-slate-900">{file.name}</span>
                <span className="mt-1 text-sm text-slate-500">{formatSize(file.size)} · Cliquez pour remplacer</span>
              </>
            ) : (
              <>
                <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sovereign-50 text-sovereign-700"><Upload className="h-7 w-7" /></span>
                <span className="font-semibold text-slate-900">Glissez le fichier ici</span>
                <span className="mt-1 text-sm text-slate-500">ou cliquez pour parcourir votre ordinateur</span>
                <span className="mt-5 text-xs text-slate-400">PDF · DOCX · Markdown · TXT · 50 Mo maximum</span>
              </>
            )}
          </button>

          {file && (
            <button type="button" onClick={() => { setFile(null); setError(''); if (inputRef.current) inputRef.current.value = ''; }} className="-mt-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
              <X className="h-4 w-4" /> Retirer le fichier
            </button>
          )}

          <div className="space-y-2">
            <Label htmlFor="document-type">Nature du document <span className="font-normal text-slate-400">(facultatif)</span></Label>
            <select id="document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)} className="input w-full" disabled={upload.isPending}>
              {DOCUMENT_TYPES.map(([value, label]) => <option key={value || 'auto'} value={value}>{label}</option>)}
            </select>
            <p className="text-xs text-slate-500">Cela aide l’audit à interpréter les clauses dans leur contexte.</p>
          </div>

          {error && (
            <div role="alert" className="flex gap-3 rounded-lg border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span>
            </div>
          )}

          <div className="flex flex-col gap-4 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="flex items-center gap-2 text-xs text-slate-500"><ShieldCheck className="h-4 w-4 text-success-600" />Le document reste isolé dans l’espace de votre organisation.</p>
            <Button onClick={startAnalysis} disabled={!file || upload.isPending} className="min-w-48">
              {upload.isPending ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Dépôt en cours…</> : <><Upload className="mr-2 h-4 w-4" />Déposer et analyser</>}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ['1', 'Extraction', 'Texte et structure du document'],
          ['2', 'Audit de conformité', 'Analyse et recherche juridique'],
          ['3', 'Rapports', 'Constats, risques et recommandations'],
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
