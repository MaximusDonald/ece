'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import Cookies from 'js-cookie';
import { api, authApi, orgApi, projectApi, documentApi, reportApi, adminApi } from '@/lib/api';
import type { Project, ProjectListItem, Document, DocumentPipeline, JobResponse, ReportVersionListItem, RiskFinding, ReportVersion, ReportDiff, LegalSource, SourceCollectionRun, LLMModelConfig, LLMProviderAvailability } from '@/lib/api';

// Auth hooks
export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.login(email, password),
    onSuccess: (response) => {
      const { access_token } = response;
      if (access_token) {
        Cookies.set('access_token', access_token, { expires: 7, sameSite: 'lax' });
      }
      // Do not reuse the previous account's cached role while a login switches identities.
      queryClient.removeQueries({ queryKey: ['me'] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => authApi.register(email, password),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      queryClient.clear();
    },
  });
}

export function useMe(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ['me'],
    queryFn: authApi.getMe,
    enabled: options.enabled ?? true,
    retry: false,
  });
}

// Organization hooks
export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => orgApi.create(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organization'] });
      queryClient.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useOrganization() {
  return useQuery({
    queryKey: ['organization'],
    queryFn: orgApi.getMe,
    retry: false,
  });
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => orgApi.updateMe(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['organization'] }),
  });
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { email?: string; password?: string }) => authApi.updateMe(data),
    onSuccess: (user) => queryClient.setQueryData(['me'], user),
  });
}

export function useOrganizationMembers(enabled = true) {
  return useQuery({
    queryKey: ['organizationMembers'],
    queryFn: orgApi.listMembers,
    enabled,
  });
}

export function useCreateOrganizationMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; password: string; role: string }) => orgApi.createMember(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['organizationMembers'] }),
  });
}

// Project hooks
export function useProjects(status?: string) {
  return useQuery({
    queryKey: ['projects', status],
    queryFn: () => projectApi.list(status),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; country_code: string; sector: string; treatments: string[] }) => projectApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => projectApi.get(id),
    enabled: !!id,
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Project> }) => projectApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projectApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

// Document hooks
export function useDocuments(projectId: string) {
  return useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => documentApi.list(projectId),
    enabled: !!projectId,
    refetchInterval: (query) =>
      query.state.data?.some((document) => document.status === 'uploaded' || document.status === 'extracting')
        ? 2000
        : false,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, file, documentType }: { projectId: string; file: File; documentType?: string }) =>
      documentApi.upload(projectId, file, documentType),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] });
    },
  });
}

export function useResumeDocumentPipeline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, documentId }: { projectId: string; documentId: string }) =>
      documentApi.resumeAnalysis(projectId, documentId),
    onSuccess: (_, { projectId, documentId }) => {
      queryClient.invalidateQueries({ queryKey: ['documentPipeline', projectId, documentId] });
      queryClient.invalidateQueries({ queryKey: ['documents', projectId] });
    },
  });
}

export function useDocumentPipeline(projectId: string, documentId: string) {
  const resume = useResumeDocumentPipeline();
  const { mutate: resumePipeline, isPending: isResuming } = resume;
  const query = useQuery({
    queryKey: ['documentPipeline', projectId, documentId],
    queryFn: () => documentApi.getPipeline(projectId, documentId),
    enabled: !!projectId && !!documentId,
    retry: false,
    refetchInterval: (current) =>
      current.state.data?.status === 'completed' || current.state.data?.status === 'failed'
        ? false
        : 2000,
  });
  const lastResumeAt = useRef(0);
  const status = query.data?.status;
  const updatedAt = query.data?.updated_at;
  useEffect(() => {
    if (!status || status === 'completed' || status === 'failed' || isResuming) return;
    const stale = updatedAt ? Date.now() - new Date(updatedAt).getTime() > 120_000 : false;
    if (status !== 'not_started' && !(status === 'running' && stale)) return;
    if (Date.now() - lastResumeAt.current < 120_000) return;
    lastResumeAt.current = Date.now();
    resumePipeline({ projectId, documentId });
  }, [documentId, projectId, isResuming, resumePipeline, status, updatedAt]);

  return { ...query, resume };
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: ({ versionId, reportType, format }: { versionId: string; reportType: 'report1' | 'report2'; format: 'pdf' | 'markdown' }) =>
      format === 'pdf'
        ? reportApi.downloadPdf(versionId, reportType)
        : reportApi.downloadMarkdown(versionId, reportType),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
}

export function useDocumentExtraction(projectId: string, documentId: string) {
  return useQuery({
    queryKey: ['extraction', projectId, documentId],
    queryFn: () => documentApi.getExtraction(projectId, documentId),
    enabled: !!projectId && !!documentId,
  });
}

export function useDocumentAnalysis(projectId: string, documentId: string, enabled = true) {
  const query = useQuery({
    queryKey: ['analysis', projectId, documentId],
    queryFn: () => documentApi.getAnalysis(projectId, documentId),
    enabled: enabled && !!projectId && !!documentId,
    retry: false,
    refetchInterval: (query) => {
      if (query.state.data) return false;
      const status = (query.state.error as { response?: { status?: number } } | null)?.response?.status;
      return !status || status === 404 ? 2000 : false;
    },
  });
  const resumeRequested = useRef<string | null>(null);
  const errorStatus = (query.error as { response?: { status?: number } } | null)?.response?.status;
  useEffect(() => {
    const key = `${projectId}:${documentId}`;
    if (!enabled || !projectId || !documentId || errorStatus !== 404 || resumeRequested.current === key) return;
    resumeRequested.current = key;
    documentApi.resumeAnalysis(projectId, documentId)
      .then(() => query.refetch())
      .catch(() => undefined);
  }, [documentId, enabled, errorStatus, projectId, query.refetch]);
  return query;
}

export function useDownloadDocument() {
  return useMutation({
    mutationFn: ({ projectId, documentId }: { projectId: string; documentId: string }) =>
      documentApi.download(projectId, documentId),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
  });
}

export function useJobStatus(projectId: string, jobId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['job', projectId, jobId],
    queryFn: () => documentApi.getJobStatus(projectId, jobId),
    enabled: enabled && !!projectId && !!jobId,
    refetchInterval: (query) => {
      if (query.state.data?.status === 'processing' || query.state.data?.status === 'pending') {
        return 2000; // Poll every 2 seconds
      }
      return false;
    },
  });
}

// Report hooks
export function useReportVersions(projectId: string) {
  return useQuery({
    queryKey: ['reportVersions', projectId],
    queryFn: () => reportApi.listVersions(projectId),
    enabled: !!projectId,
  });
}

export function useReportVersion(versionId: string) {
  return useQuery({
    queryKey: ['reportVersion', versionId],
    queryFn: () => reportApi.getVersion(versionId),
    enabled: !!versionId,
  });
}

export function useReportFindings(versionId: string, filters?: { risk_level?: string; confidence?: string }) {
  return useQuery({
    queryKey: ['reportFindings', versionId, filters],
    queryFn: () => reportApi.getFindings(versionId, filters),
    enabled: !!versionId,
  });
}

export function useAddContext() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ versionId, contextData }: { versionId: string; contextData: Record<string, any> }) =>
      reportApi.addContext(versionId, contextData),
    onSuccess: (_, { versionId }) => {
      queryClient.invalidateQueries({ queryKey: ['reportVersion', versionId] });
      queryClient.invalidateQueries({ queryKey: ['reportVersions'] });
      queryClient.invalidateQueries({ queryKey: ['reportFindings'] });
    },
  });
}

export function useReportDiff(versionId: string, compareWith: string, reportType: 'report1' | 'report2') {
  return useQuery({
    queryKey: ['reportDiff', versionId, compareWith, reportType],
    queryFn: () => reportApi.getDiff(versionId, compareWith, reportType),
    enabled: !!versionId && !!compareWith,
  });
}

// Admin hooks
export function useAdminSources(params?: { status?: string; country_code?: string; level?: string }) {
  return useQuery({
    queryKey: ['adminSources', params],
    queryFn: () => adminApi.listSources(params),
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LegalSource>) => adminApi.createSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminSources'] });
    },
  });
}

export function useUpdateSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LegalSource> }) => adminApi.updateSource(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminSources'] });
    },
  });
}

export function useVerifySource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.verifySource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminSources'] });
    },
  });
}

export function useCollectSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminApi.collectSource(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['adminSources'] });
      queryClient.invalidateQueries({ queryKey: ['adminSourceCollections', id] });
    },
  });
}

export function useAdminSourceCollections(sourceId?: string) {
  return useQuery<SourceCollectionRun[]>({
    queryKey: ['adminSourceCollections', sourceId],
    queryFn: () => adminApi.listSourceCollections(sourceId!),
    enabled: Boolean(sourceId),
    refetchInterval: (query) =>
      query.state.data?.some((run) => run.status === 'queued' || run.status === 'running') ? 2000 : false,
  });
}

export function useAdminRules() {
  return useQuery<any[]>({
    queryKey: ['adminRules'],
    queryFn: adminApi.listRules,
  });
}

export function useCreateRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => adminApi.createRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminRules'] });
    },
  });
}

export function useUpdateRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => adminApi.updateRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminRules'] });
    },
  });
}

export function useAdminModels() {
  return useQuery<LLMModelConfig[]>({
    queryKey: ['adminModels'],
    queryFn: adminApi.listModels,
  });
}

export function useAdminModelProviders() {
  return useQuery<LLMProviderAvailability[]>({
    queryKey: ['adminModelProviders'],
    queryFn: adminApi.listModelProviders,
  });
}

export function useCreateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => adminApi.createModel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminModels'] });
    },
  });
}

export function useUpdateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => adminApi.updateModel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminModels'] });
    },
  });
}

export function useAdminCountries() {
  return useQuery<any[]>({
    queryKey: ['adminCountries'],
    queryFn: adminApi.listCountries,
  });
}

export function useUpdateCountry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, data }: { code: string; data: { is_active: boolean } }) => adminApi.updateCountry(code, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminCountries'] });
    },
  });
}

export function useAdminUsers() {
  return useQuery<any[]>({
    queryKey: ['adminUsers'],
    queryFn: adminApi.listUsers,
  });
}

export function useCreatePlatformAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; password: string }) => adminApi.createPlatformAdmin(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['adminUsers'] }),
  });
}

export function useAdminAuditLogs(params?: { entity_type?: string; user_id?: string }) {
  return useQuery<any[]>({
    queryKey: ['adminAuditLogs', params],
    queryFn: () => adminApi.listAuditLogs(params),
  });
}
