'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { useDocuments, useUploadDocument } from '@/hooks/useApi';
import { Upload, FileText, Download, Trash2, Eye, Clock, CheckCircle } from 'lucide-react';
import { formatDateTime, formatDate } from '@/lib/utils';
import { useState } from 'react';

export function ProjectWorkspaceDocuments({ projectId }: { projectId: string }) {
  const { data: documents, isLoading, refetch } = useDocuments(projectId);
  const uploadMutation = useUploadDocument();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');

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
        alert('Type de fichier non autorisé. Formats acceptés : PDF, DOCX, Markdown, Texte');
        return;
      }
      // Validate size (50 MB)
      if (file.size > 50 * 1024 * 1024) {
        alert('Fichier trop volumineux. Taille maximale : 50 Mo');
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
      alert('Erreur lors du téléversement');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <Badge variant="conforme"><CheckCircle className="h-3 w-3 mr-1" />Terminé</Badge>;
      case 'processing': return <Badge variant="modere"><Clock className="h-3 w-3 mr-1" />En cours</Badge>;
      case 'extracting': return <Badge variant="a_surveiller"><Clock className="h-3 w-3 mr-1" />Extraction</Badge>;
      case 'failed': return <Badge variant="critique">Échoué</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
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
                    <TableCell>{getStatusBadge(doc.status)}</TableCell>
                    <TableCell>{formatDateTime(doc.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {doc.status === 'completed' && (
                          <>
                            <Button variant="ghost" size="icon" asChild>
                              <Link href={`/dashboard/projects/${projectId}/documents/${doc.id}/extraction`}>
                                <Eye className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button variant="ghost" size="icon">
                              <Download className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        <Button variant="ghost" size="icon" className="text-danger-600 hover:text-danger-700">
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
    </div>
  );
}

import Link from 'next/link';