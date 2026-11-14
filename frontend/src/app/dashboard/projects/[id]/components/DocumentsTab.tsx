'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useDocuments, useDocumentAnalysis, useUploadDocument, useDownloadDocument, useDeleteDocument, useResumeDocumentPipeline } from '@/hooks/useApi';
import { Upload, FileText, Download, Trash2, Eye, CheckCircle, Loader2, AlertCircle, X, RotateCw, Pencil } from 'lucide-react';
import { formatDateTime, formatDate } from '@/lib/utils';
import { useRef, useState } from 'react';
import { toast } from '@/hooks/use-toast';
import Link from 'next/link';
import { ContextDocumentModal } from './ContextDocumentModal';

type QueuedUploadItem = {
  id: string;
  file: File;
  documentType: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
};

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.md', '.txt'];
const MAX_FILE_SIZE = 50 * 1024 * 1024;
const DOCUMENT_TYPE_OPTIONS = [
  { value: '', label: 'Détection automatique' },
  { value: 'cahier_charges', label: 'Cahier des charges' },
  { value: 'privacy_policy', label: 'Politique de confidentialité' },
  { value: 'contract', label: 'Contrat' },
  { value: 'terms_conditions', label: 'Conditions générales' },
  { value: 'internal_procedure', label: 'Procédure interne' },
  { value: 'compliance_dossier', label: 'Dossier de conformité' },
  { value: 'technical_specs', label: 'Spécifications techniques' },
  { value: 'governance', label: 'Gouvernance des données' },
];

export function ProjectWorkspaceDocuments({ projectId }: { projectId: string }) {
  const { data: documents, isLoading, refetch } = useDocuments(projectId);
  const uploadMutation = useUploadDocument();
  const downloadMutation = useDownloadDocument();
  const deleteMutation = useDeleteDocument();
  const resumeMutation = useResumeDocumentPipeline();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [queuedFiles, setQueuedFiles] = useState<QueuedUploadItem[]>([]);
  const [defaultDocumentType, setDefaultDocumentType] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isBatchUploading, setIsBatchUploading] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<{ id: string; filename: string } | null>(null);
  const [isContextDocOpen, setIsContextDocOpen] = useState(false);

  const addFilesToQueue = (fileList: FileList | File[] | null) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    const rejected: string[] = [];
    const newItems: QueuedUploadItem[] = [];

    for (const file of files) {
      const lowerName = file.name.toLowerCase();
      if (!ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
        rejected.push(`${file.name} (format non pris en charge)`);
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        rejected.push(`${file.name} (> 50 Mo)`);
        continue;
      }
      const alreadyQueued = queuedFiles.some(
        (q) => q.file.name === file.name && q.file.size === file.size && q.status !== 'done',
      );
      if (!alreadyQueued) {
        newItems.push({
          id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          file,
          documentType: defaultDocumentType,
          status: 'pending',
        });
      }
    }

    if (rejected.length > 0) {
      toast({
        title: 'Certains fichiers ont été ignorés',
        description: rejected.join(', '),
        variant: 'destructive',
      });
    }

    if (newItems.length > 0) {
      setQueuedFiles((prev) => [...prev, ...newItems]);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFilesToQueue(e.target.files);
  };

  const handleUpload = async () => {
    const itemsToUpload = queuedFiles.filter((item) => item.status === 'pending' || item.status === 'error');
    if (itemsToUpload.length === 0) return;

    setIsBatchUploading(true);
    let successCount = 0;
    let errorCount = 0;

    // Upload concurrently in batches of 3 to stay fast without saturating the connection
    const BATCH_SIZE = 3;
    for (let i = 0; i < itemsToUpload.length; i += BATCH_SIZE) {
      const batch = itemsToUpload.slice(i, i + BATCH_SIZE);
      await Promise.all(
        batch.map(async (item) => {
          setQueuedFiles((prev) =>
            prev.map((q) => (q.id === item.id ? { ...q, status: 'uploading', error: undefined } : q)),
          );
          try {
            await uploadMutation.mutateAsync({
              projectId,
              file: item.file,
              documentType: item.documentType || undefined,
            });
            successCount += 1;
            setQueuedFiles((prev) =>
              prev.map((q) => (q.id === item.id ? { ...q, status: 'done' } : q)),
            );
          } catch (err) {
            errorCount += 1;
            const apiError = err as { response?: { data?: { detail?: string } } };
            const message = apiError.response?.data?.detail || 'Échec du téléversement';
            setQueuedFiles((prev) =>
              prev.map((q) => (q.id === item.id ? { ...q, status: 'error', error: message } : q)),
            );
          }
        }),
      );
    }

    setIsBatchUploading(false);
    await refetch();

    if (errorCount === 0 && successCount > 0) {
      toast({
        title: successCount > 1 ? `${successCount} documents téléversés` : 'Document téléversé',
        description: 'L’extraction et l’analyse juridique ont été lancées en arrière-plan.',
      });
      setIsUploadOpen(false);
      setQueuedFiles([]);
      setDefaultDocumentType('');
    } else if (successCount > 0 && errorCount > 0) {
      toast({
        title: `${successCount} réussi(s), ${errorCount} en échec`,
        description: 'Vous pouvez réessayer les fichiers en erreur ou les retirer.',
        variant: 'destructive',
      });
    } else {
      toast({
        title: 'Téléversement impossible',
        description: 'Aucun document n’a pu être envoyé. Vérifiez les erreurs affichées.',
        variant: 'destructive',
      });
    }
  };

  const closeUploadModal = () => {
    if (isBatchUploading) return;
    setIsUploadOpen(false);
    setQueuedFiles([]);
    setDefaultDocumentType('');
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle>Documents du projet</CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setIsContextDocOpen(true)}>
              <Pencil className="h-4 w-4 mr-2" />
              Contexte complémentaire
            </Button>
            <Button onClick={() => setIsUploadOpen(true)} disabled={isBatchUploading}>
              <Upload className="h-4 w-4 mr-2" />
              Téléverser des documents
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Documents Table */}
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : documents && documents.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Taille</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-slate-400" />
                        <span className="font-medium">{doc.filename}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {doc.mime_type === 'application/pdf' ? 'PDF' :
                         doc.mime_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ? 'DOCX' :
                         'MD/TXT'}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatSize(doc.size_bytes)}</TableCell>
                    <TableCell><DocumentStatusBadge projectId={projectId} document={doc} /></TableCell>
                    <TableCell>{formatDateTime(doc.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {doc.status === 'extracted' && (
                          <>
                            {doc.document_type === 'contexte_complementaire' && (
                              <Button
                                variant="ghost"
                                size="icon"
                                title="Consulter / Modifier le contexte"
                                aria-label="Consulter / Modifier le contexte"
                                onClick={() => setIsContextDocOpen(true)}
                              >
                                <Pencil className="h-4 w-4 text-sovereign-600" />
                              </Button>
                            )}
                            <Button variant="ghost" size="icon" asChild>
                              <Link href={`/dashboard/projects/${projectId}/documents/${doc.id}/extraction`}>
                                <Eye className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button variant="ghost" size="icon" aria-label="Télécharger le document" disabled={downloadMutation.isPending} onClick={() => downloadMutation.mutate({ projectId, documentId: doc.id }, { onError: () => toast({ title: 'Téléchargement impossible', description: 'Le document n’a pas pu être téléchargé. Réessayez dans un instant.', variant: 'destructive' }) })}>
                              {downloadMutation.isPending && downloadMutation.variables?.documentId === doc.id
                                ? <Loader2 className="h-4 w-4 animate-spin" />
                                : <Download className="h-4 w-4" />}
                            </Button>
                          </>
                        )}
                        {doc.status === 'failed' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-sovereign-600 hover:text-sovereign-700"
                            disabled={resumeMutation.isPending}
                            onClick={() =>
                              resumeMutation.mutate(
                                { projectId, documentId: doc.id },
                                {
                                  onSuccess: () => {
                                    toast({ title: 'Analyse relancée', description: `Le traitement de ${doc.filename} a redémarré.` });
                                    refetch();
                                  },
                                  onError: () =>
                                    toast({ title: 'Relance impossible', description: 'Impossible de relancer ce document.', variant: 'destructive' }),
                                },
                              )
                            }
                          >
                            <RotateCw className={`h-4 w-4 mr-1 ${resumeMutation.isPending && resumeMutation.variables?.documentId === doc.id ? 'animate-spin' : ''}`} />
                            Relancer
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-danger-600 hover:text-danger-700"
                          disabled={deleteMutation.isPending}
                          onClick={() => setDocumentToDelete({ id: doc.id, filename: doc.filename })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-xl">
              <Upload className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun document</h3>
              <p className="text-slate-500 mb-4">Téléversez votre premier document pour commencer l'analyse.</p>
              <Button onClick={() => setIsUploadOpen(true)}>
                <Upload className="h-4 w-4 mr-2" />
                Téléverser des documents
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Modal (Multi-fichiers) */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={closeUploadModal}>
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Téléverser des documents</h2>
                <p className="text-sm text-slate-500 mt-0.5">Sélectionnez ou déposez un ou plusieurs fichiers simultanément.</p>
              </div>
              <button onClick={closeUploadModal} disabled={isBatchUploading} className="text-slate-400 hover:text-slate-600 disabled:opacity-40">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              <div
                onDragOver={(e) => { e.preventDefault(); if (!isBatchUploading) setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (!isBatchUploading) addFilesToQueue(e.dataTransfer.files);
                }}
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                  isDragging
                    ? 'border-sovereign-500 bg-sovereign-50'
                    : 'border-slate-300 hover:border-sovereign-400'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.md,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                  disabled={isBatchUploading}
                />
                <label htmlFor="file-upload" className={`block ${isBatchUploading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}>
                  <Upload className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-slate-700 font-medium mb-1">Cliquez ou glissez-déposez vos fichiers ici</p>
                  <p className="text-xs text-slate-400">PDF, DOCX, Markdown, Texte · Sélection multiple autorisée (max 50 Mo / fichier)</p>
                </label>
              </div>

              <div>
                <label className="label">Type par défaut pour les nouveaux fichiers (optionnel)</label>
                <select
                  value={defaultDocumentType}
                  onChange={(e) => {
                    const val = e.target.value;
                    setDefaultDocumentType(val);
                    setQueuedFiles((prev) =>
                      prev.map((q) => (q.status === 'pending' ? { ...q, documentType: val } : q)),
                    );
                  }}
                  className="input"
                  disabled={isBatchUploading}
                >
                  {DOCUMENT_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value || 'auto'} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {queuedFiles.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">
                      {queuedFiles.length} fichier{queuedFiles.length > 1 ? 's' : ''} sélectionné{queuedFiles.length > 1 ? 's' : ''}
                    </span>
                    {!isBatchUploading && (
                      <button
                        type="button"
                        onClick={() => setQueuedFiles([])}
                        className="text-xs text-slate-500 hover:text-danger-600"
                      >
                        Tout retirer
                      </button>
                    )}
                  </div>
                  <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                    {queuedFiles.map((item) => (
                      <div
                        key={item.id}
                        className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-lg border text-sm ${
                          item.status === 'done'
                            ? 'bg-emerald-50/70 border-emerald-200'
                            : item.status === 'error'
                            ? 'bg-danger-50 border-danger-200'
                            : 'bg-slate-50 border-slate-200'
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          {item.status === 'uploading' && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-sovereign-600" />}
                          {item.status === 'done' && <CheckCircle className="h-4 w-4 shrink-0 text-emerald-600" />}
                          {item.status === 'error' && <AlertCircle className="h-4 w-4 shrink-0 text-danger-600" />}
                          {item.status === 'pending' && <FileText className="h-4 w-4 shrink-0 text-slate-400" />}
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-slate-800 truncate">{item.file.name}</p>
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
                            className="text-xs border border-slate-300 rounded-md px-2 py-1 bg-white"
                            aria-label={`Type de document pour ${item.file.name}`}
                          >
                            {DOCUMENT_TYPE_OPTIONS.map((opt) => (
                              <option key={opt.value || 'auto'} value={opt.value}>{opt.label}</option>
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
            </div>

            <div className="p-6 flex justify-end gap-3 border-t border-slate-200 bg-slate-50/50 rounded-b-xl">
              <Button variant="secondary" onClick={closeUploadModal} disabled={isBatchUploading}>
                Annuler
              </Button>
              <Button
                onClick={handleUpload}
                disabled={
                  queuedFiles.filter((q) => q.status === 'pending' || q.status === 'error').length === 0 ||
                  isBatchUploading
                }
              >
                {isBatchUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Téléversement ({queuedFiles.filter((q) => q.status === 'done').length}/{queuedFiles.length})...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Téléverser ({queuedFiles.filter((q) => q.status === 'pending' || q.status === 'error').length})
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {documentToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setDocumentToDelete(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 text-danger-600">
              <AlertCircle className="h-6 w-6" />
              <h3 className="text-lg font-semibold text-slate-900">Supprimer le document ?</h3>
            </div>
            <p className="text-sm text-slate-600">
              Êtes-vous sûr de vouloir supprimer <span className="font-semibold text-slate-800">{documentToDelete.filename}</span> ? Cette action effacera également les extractions et analyses associées.
            </p>
            <div className="flex justify-end gap-3 pt-3">
              <Button
                variant="secondary"
                onClick={() => setDocumentToDelete(null)}
                disabled={deleteMutation.isPending}
              >
                Annuler
              </Button>
              <Button
                variant="destructive"
                disabled={deleteMutation.isPending}
                onClick={async () => {
                  try {
                    await deleteMutation.mutateAsync({ projectId, documentId: documentToDelete.id });
                    toast({ title: 'Document supprimé', description: 'Le document et ses analyses ont été retirés.' });
                    setDocumentToDelete(null);
                  } catch {
                    toast({ title: 'Erreur', description: 'Impossible de supprimer le document.', variant: 'destructive' });
                  }
                }}
              >
                {deleteMutation.isPending ? 'Suppression...' : 'Supprimer'}
              </Button>
            </div>
          </div>
        </div>
      )}
      {isContextDocOpen && (
        <ContextDocumentModal
          projectId={projectId}
          onClose={() => setIsContextDocOpen(false)}
        />
      )}
    </div>
  );
}

function DocumentStatusBadge({ projectId, document }: { projectId: string; document: { id: string; status: string } }) {
  const analysisQuery = useDocumentAnalysis(projectId, document.id, document.status === 'extracted');

  if (document.status === 'uploaded') {
    return <span className="inline-flex items-center gap-2"><Badge variant="secondary">Téléversé</Badge><Loader2 className="h-4 w-4 animate-spin text-sovereign-600" aria-label="Extraction en cours" /></span>;
  }
  if (document.status === 'extracting') {
    return <Badge variant="a_surveiller"><Loader2 className="mr-1 h-3 w-3 animate-spin" />Extraction en cours</Badge>;
  }
  if (document.status === 'extracted') {
    const errorStatus = (analysisQuery.error as { response?: { status?: number } } | null)?.response?.status;
    if (analysisQuery.isError && errorStatus !== 404) {
      return <Badge variant="critique"><AlertCircle className="mr-1 h-3 w-3" />Analyse indisponible</Badge>;
    }
    return analysisQuery.data
      ? <Badge variant="conforme"><CheckCircle className="mr-1 h-3 w-3" />Analyse terminée</Badge>
      : <Badge variant="modere"><Loader2 className="mr-1 h-3 w-3 animate-spin" />Analyses en cours</Badge>;
  }
  if (document.status === 'failed') {
    return <Badge variant="critique"><AlertCircle className="mr-1 h-3 w-3" />Échec</Badge>;
  }
  return <Badge variant="secondary">{document.status}</Badge>;
}
