'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useDocuments, useDocumentAnalysis, useUploadDocument, useDownloadDocument, useDeleteDocument } from '@/hooks/useApi';
import { Upload, FileText, Download, Trash2, Eye, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { formatDateTime, formatDate } from '@/lib/utils';
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';
import Link from 'next/link';

export function ProjectWorkspaceDocuments({ projectId }: { projectId: string }) {
  const { data: documents, isLoading, refetch } = useDocuments(projectId);
  const uploadMutation = useUploadDocument();
  const downloadMutation = useDownloadDocument();
  const deleteMutation = useDeleteDocument();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');
  const [documentToDelete, setDocumentToDelete] = useState<{ id: string; filename: string } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/markdown',
        'text/plain',
      ];
      if (!allowedTypes.includes(file.type)) {
        toast({ title: 'Format non pris en charge', description: 'Choisissez un fichier PDF, DOCX, Markdown ou texte.', variant: 'destructive' });
        return;
      }
      // Validate size (50 MB)
      if (file.size > 50 * 1024 * 1024) {
        toast({ title: 'Fichier trop volumineux', description: 'La taille maximale autorisée est de 50 Mo.', variant: 'destructive' });
        return;
      }
      setUploadFile(file);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    try {
      await uploadMutation.mutateAsync({
        projectId,
        file: uploadFile,
        documentType: documentType || undefined,
      });
      setIsUploadOpen(false);
      setUploadFile(null);
      setDocumentType('');
      refetch();
    } catch (err) {
      toast({ title: 'Téléversement impossible', description: 'Le document n’a pas pu être envoyé. Réessayez dans un instant.', variant: 'destructive' });
    }
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
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Documents du projet</CardTitle>
          <Button onClick={() => setIsUploadOpen(true)} disabled={uploadMutation.isPending}>
            <Upload className="h-4 w-4 mr-2" />
            Téléverser un document
          </Button>
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
                Téléverser un document
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setIsUploadOpen(false)}>
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Téléverser un document</h2>
              <button onClick={() => setIsUploadOpen(false)} className="text-slate-400 hover:text-slate-600">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-sovereign-400 transition-colors">
                <input
                  type="file"
                  accept=".pdf,.docx,.md,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                  disabled={uploadMutation.isPending}
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-600 mb-1">Cliquez ou glissez-déposez un fichier</p>
                  <p className="text-sm text-slate-400">PDF, DOCX, Markdown, Texte (max 50 Mo)</p>
                </label>
                {uploadFile && (
                  <div className="mt-3 p-3 bg-sovereign-50 border border-sovereign-200 rounded-lg">
                    <p className="font-medium text-sovereign-700">{uploadFile.name}</p>
                    <p className="text-sm text-sovereign-600">{formatSize(uploadFile.size)}</p>
                  </div>
                )}
              </div>

              <div>
                <label className="label">Type de document (optionnel)</label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  className="input"
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

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button variant="secondary" onClick={() => setIsUploadOpen(false)} disabled={uploadMutation.isPending}>
                  Annuler
                </Button>
                <Button onClick={handleUpload} disabled={!uploadFile || uploadMutation.isPending}>
                  {uploadMutation.isPending ? 'Téléversement...' : 'Téléverser'}
                </Button>
              </div>
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
