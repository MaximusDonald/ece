import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const http = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add auth token
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = Cookies.get('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get('refresh_token');
        if (refreshToken) {
          const response = await axios.post(
            `${API_URL}/api/auth/jwt/refresh`,
            { refresh_token: refreshToken },
            { withCredentials: true }
          );

          const { access_token } = response.data;
          Cookies.set('access_token', access_token, { expires: 7 });

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }

          return http(originalRequest);
        }
      } catch {
        // Refresh failed, redirect to login
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');
        window.location.href = '/auth/login';
      }
    }

    return Promise.reject(error);
  }
);

// Keep the public API client focused on response bodies. TanStack Query pages
// consume domain data, not Axios transport envelopes.
export const api = {
  get: <T = any>(url: string, config?: AxiosRequestConfig) =>
    http.get<T>(url, config).then((response) => response.data),
  post: <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    http.post<T>(url, data, config).then((response) => response.data),
  put: <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    http.put<T>(url, data, config).then((response) => response.data),
  patch: <T = any>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    http.patch<T>(url, data, config).then((response) => response.data),
  delete: <T = any>(url: string, config?: AxiosRequestConfig) =>
    http.delete<T>(url, config).then((response) => response.data),
};

// Types
export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  role: string;
  org_id: string | null;
  created_at: string;
}

export type LLMProvider = 'openai' | 'anthropic' | 'gemini' | 'groq';

export interface LLMModelConfig {
  id: string;
  name: string;
  provider: LLMProvider;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt_version: string;
  system_prompt: string;
  is_active: boolean;
  is_default: boolean;
  available: boolean;
  rpm_limit?: number | null;
  tpm_limit?: number | null;
  rpd_limit?: number | null;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderAvailability {
  provider: LLMProvider;
  label: string;
  available: boolean;
  default_model: string;
}

export interface Organization {
  id: string;
  name: string;
  plan: string;
  created_at: string;
}

export interface OrganizationMember {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  country_code: string;
  sector: string;
  treatments: string[];
  represented_entity_type: string;
  represented_entity_other?: string | null;
  represented_role_details?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListItem {
  id: string;
  name: string;
  country_code: string;
  sector: string;
  status: string;
  risk_score: number | null;
  last_analysis: string | null;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  document_type?: string | null;
  mime_type: string;
  minio_bucket: string;
  minio_object: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface DocumentExtraction {
  id: string;
  document_id: string;
  markdown: string;
  quality_score: number;
  page_count: number;
  language: string;
  created_at: string;
}

export interface DocumentAnalysis {
  id: string;
  extraction_id: string;
  entities: Record<string, any>;
  vague_zones: VagueZone[];
  created_at: string;
}

export interface VagueZone {
  clause_ref: string;
  description: string;
  suggested_fields: string[];
}

export interface MatchedSourceDetail {
  id: string;
  title: string;
  authority: string;
  original_filename?: string | null;
  download_url?: string | null;
  level?: string | null;
  article_ref?: string | null;
}

export interface MatchedArticleDetail {
  id: string;
  text_code: string;
  text_title: string;
  jurisdiction: string;
  authority: string;
  article_number: string;
  title?: string | null;
  section_breadcrumb: string;
  full_text: string;
  has_sanction: boolean;
  sanction_details?: string | null;
  compliance_rule_type?: string | null;
  official_url?: string | null;
}

export interface LegalTextItem {
  id: string;
  code: string;
  title: string;
  jurisdiction: string;
  authority: string;
  level: string;
  publication_date?: string | null;
  status: string;
  official_url?: string | null;
  pdf_path?: string | null;
  text_path?: string | null;
  sha256_hash?: string | null;
  total_articles: number;
  created_at: string;
  updated_at: string;
}

export interface CorpusSectionItem {
  id: string;
  text_id: string;
  parent_section_id?: string | null;
  level_name: string;
  title: string;
  breadcrumb: string;
  order_index: number;
  article_count: number;
  created_at: string;
}

export interface CorpusArticleItem {
  id: string;
  text_id: string;
  section_id?: string | null;
  article_number: string;
  order_index: number;
  title?: string | null;
  full_text: string;
  topics: string[];
  actors: string[];
  has_sanction: boolean;
  sanction_details?: string | null;
  compliance_rule_type?: string | null;
  ai_tagged: boolean;
  text_code: string;
  text_title: string;
  jurisdiction: string;
  authority: string;
  section_breadcrumb: string;
  official_url?: string | null;
  prev_article_id?: string | null;
  next_article_id?: string | null;
  score?: number | null;
  created_at: string;
  updated_at: string;
}

export interface CorpusArticlePage {
  items: CorpusArticleItem[];
  total: number;
  skip: number;
  limit: number;
  mode: string;
}

export interface CorpusSummary {
  total_texts: number;
  total_sections: number;
  total_articles: number;
  sanctioned_articles: number;
  ai_tagged_articles: number;
  jurisdictions: string[];
}

export interface RiskFinding {
  id: string;
  report_version_id: string;
  clause_ref: string;
  finding_text: string;
  risk_level: string;
  confidence: string;
  matched_sources: string[];
  matched_articles?: string[];
  sources_details?: MatchedSourceDetail[];
  articles_details?: MatchedArticleDetail[];
  obsolescence_flag: boolean;
  conflict_flag: boolean;
  conflict_details: string | null;
  recommendation: string;
  legal_nature?: 'non_conformite_imperative' | 'risque_contractuel' | 'bonne_pratique' | string;
  review_status?: 'pending' | 'validated' | 'mitigated_by_evidence' | 'dismissed' | string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_note?: string | null;
  created_at: string;
}

export interface ReportVersion {
  id: string;
  project_id: string;
  version: string;
  global_score: number;
  confidence_global: string;
  severity_counts: Record<string, number>;
  report1_markdown: string;
  report2_markdown: string;
  report1_pdf_minio: string | null;
  report2_pdf_minio: string | null;
  parent_version_id: string | null;
  created_at: string;
}

export interface ReportVersionListItem {
  id: string;
  version: string;
  global_score: number;
  confidence_global: string;
  severity_counts: Record<string, number>;
  created_at: string;
  parent_version_id?: string | null;
}

export interface JobResponse {
  job_id: string;
  status: string;
  steps: JobStep[];
  estimated_remaining_seconds: number | null;
  result: Record<string, any> | null;
  error: string | null;
}

export interface DocumentPipelineStep {
  step: number;
  key: string;
  label: string;
  status: 'pending' | 'running' | 'retrying' | 'completed' | 'failed';
  message: string;
}

export interface DocumentPipeline {
  document_id: string;
  filename: string | null;
  status: 'not_started' | 'queued' | 'running' | 'completed' | 'failed';
  current_step: number | null;
  progress: number;
  steps: DocumentPipelineStep[];
  error: string | null;
  warnings: string[];
  report_version_id: string | null;
  updated_at: string | null;
}

export interface JobStep {
  step: number;
  name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface LegalSource {
  id: string;
  title: string;
  authority: string;
  country_code: string | null;
  level: string;
  article_ref: string;
  url_official: string;
  content_hash: string;
  content_text: string;
  status: string;
  effective_date: string | null;
  abrogated_date: string | null;
  embedding?: number[];
  created_at: string;
  updated_at: string;
  collection_enabled: boolean;
  last_collection_at: string | null;
  last_successful_collection_at: string | null;
  last_collection_status: string | null;
  last_collection_run_id: string | null;
  source_etag: string | null;
  source_last_modified: string | null;
  is_portal?: boolean;
  parent_source_id?: string | null;
  original_filename?: string | null;
  download_url?: string | null;
  minio_object_path?: string | null;
  legal_terms?: Record<string, any>;
  extracted_articles?: Array<{
    article_ref?: string;
    title?: string;
    content_summary?: string;
    has_sanction?: boolean;
    sanction_details?: string | null;
  }>;
  summary?: string | null;
  crawl_depth?: number;
  child_documents_count?: number;
}

export interface LegalDocumentItem {
  id: string;
  parent_source_id: string | null;
  parent_title?: string | null;
  parent_authority?: string | null;
  title: string;
  authority: string;
  country_code: string | null;
  level: string;
  original_filename: string | null;
  download_url: string | null;
  minio_object_path: string | null;
  summary: string | null;
  legal_terms: Record<string, any>;
  extracted_articles: Array<{
    article_ref?: string;
    title?: string;
    content_summary?: string;
    has_sanction?: boolean;
    sanction_details?: string | null;
  }>;
  article_count: number;
  content_hash: string;
  created_at: string;
  updated_at: string;
}

export interface SourceCollectionRun {
  id: string;
  source_id: string;
  trigger_type: 'manual' | 'scheduled';
  triggered_by: string | null;
  status: 'queued' | 'running' | 'succeeded' | 'unchanged' | 'failed';
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  http_status_code: number | null;
  previous_hash: string | null;
  collected_hash: string | null;
  changed: boolean | null;
  discovered_urls_count?: number;
  downloaded_files_count?: number;
  ai_processed_count?: number;
  error_message?: string | null;
}

export interface RegulatoryAlertItem {
  id: string;
  source_id: string;
  collection_run_id?: string | null;
  jurisdiction: string;
  authority: string;
  title: string;
  detected_url: string;
  document_filename?: string | null;
  previous_hash?: string | null;
  new_hash: string;
  etag?: string | null;
  change_summary: string;
  status: 'pending_review' | 'approved' | 'dismissed';
  review_note?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  detected_at: string;
}

export interface DiffLine {
  type: 'added' | 'removed' | 'unchanged' | 'modified';
  content: string;
  line_number_old: number | null;
  line_number_new: number | null;
}

export interface ReportDiff {
  version_old: string;
  version_new: string;
  report_type: string;
  diff_lines: DiffLine[];
  summary: Record<string, number>;
}

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    // FastAPI Users exposes the JWT login as an OAuth2 password form endpoint.
    api.post<{ access_token: string; token_type: string }>(
      '/auth/jwt/login',
      new URLSearchParams({ username: email, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    ),

  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password }),

  logout: () =>
    api.post('/auth/jwt/logout'),

  getMe: () =>
    api.get<User>('/auth/users/me'),

  updateMe: (data: Partial<User> & { password?: string }) =>
    api.patch<User>('/auth/users/me', data),
};

// Organization API
export const orgApi = {
  create: (name: string) =>
    api.post<Organization>('/projects/organization', { name }),

  getMe: () =>
    api.get<Organization>('/projects/organization/me'),

  updateMe: (name: string) =>
    api.patch<Organization>('/projects/organization/me', { name }),

  listMembers: () =>
    api.get<OrganizationMember[]>('/projects/organization/members'),

  createMember: (data: { email: string; password: string; role: string }) =>
    api.post<OrganizationMember>('/projects/organization/members', data),
};

// Project API
export const projectApi = {
  list: (status?: string) =>
    api.get<ProjectListItem[]>('/projects', { params: { status } }),

  create: (data: {
    name: string;
    country_code: string;
    sector: string;
    treatments: string[];
    represented_entity_type: string;
    represented_entity_other?: string;
    represented_role_details?: string;
  }) =>
    api.post<Project>('/projects', data),

  get: (id: string) =>
    api.get<Project>(`/projects/${id}`),

  update: (id: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${id}`, data),

  delete: (id: string) =>
    api.delete(`/projects/${id}`),
};

// Document API
export const documentApi = {
  upload: (projectId: string, file: File, documentType?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (documentType) formData.append('document_type', documentType);
    return api.post<Document>(`/projects/${projectId}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  list: (projectId: string) =>
    api.get<Document[]>(`/projects/${projectId}/documents`),

  get: (projectId: string, documentId: string) =>
    api.get<Document>(`/projects/${projectId}/documents/${documentId}`),

  getExtraction: (projectId: string, documentId: string) =>
    api.get<DocumentExtraction>(`/projects/${projectId}/documents/${documentId}/extraction`),

  getAnalysis: (projectId: string, documentId: string) =>
    api.get<DocumentAnalysis>(`/projects/${projectId}/documents/${documentId}/analysis`),

  getPipeline: (projectId: string, documentId: string) =>
    api.get<DocumentPipeline>(`/projects/${projectId}/documents/${documentId}/pipeline`),

  resumeAnalysis: (projectId: string, documentId: string) =>
    api.post<{ status: string; stage: string; job_id?: string | null }>(
      `/projects/${projectId}/documents/${documentId}/resume`,
    ),

  download: async (projectId: string, documentId: string) => {
    const response = await http.get<Blob>(
      `/projects/${projectId}/documents/${documentId}/download`,
      { responseType: 'blob' },
    );
    const disposition = response.headers['content-disposition'] as string | undefined;
    const encodedName = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    const plainName = disposition?.match(/filename="?([^";]+)"?/i)?.[1];
    let filename = 'document';
    try {
      filename = encodedName ? decodeURIComponent(encodedName) : plainName || filename;
    } catch {
      filename = plainName || filename;
    }
    return { blob: response.data, filename };
  },

  delete: (projectId: string, documentId: string) =>
    api.delete<void>(`/projects/${projectId}/documents/${documentId}`),

  getJobStatus: (projectId: string, jobId: string) =>
    api.get<JobResponse>(`/projects/${projectId}/documents/jobs/${jobId}`),

  getContextDocument: (projectId: string) =>
    api.get<{
      document_id: string;
      filename: string;
      markdown: string;
      entities: Record<string, any>;
      updated_at: string;
    } | null>(`/projects/${projectId}/documents/context-document`),

  updateContextDocument: (
    projectId: string,
    payload: { markdown?: string; context_data?: Record<string, any>; trigger_report_update?: boolean },
  ) =>
    api.put<{
      document_id: string;
      filename: string;
      markdown: string;
      entities: Record<string, any>;
      updated_at: string;
      job_id?: string | null;
    }>(`/projects/${projectId}/documents/context-document`, payload),
};

// Report API
export const reportApi = {
  listVersions: (projectId: string) =>
    api.get<ReportVersionListItem[]>(`/reports/projects/${projectId}`),

  getVersion: (versionId: string) =>
    api.get<ReportVersion>(`/reports/${versionId}`),

  getFindings: (versionId: string, filters?: { risk_level?: string; confidence?: string }) =>
    api.get<RiskFinding[]>(`/reports/${versionId}/findings`, { params: filters }),

  reviewFinding: (
    findingId: string,
    payload: {
      review_status: 'pending' | 'validated' | 'mitigated_by_evidence' | 'dismissed';
      legal_nature?: 'non_conformite_imperative' | 'risque_contractuel' | 'bonne_pratique';
      review_note?: string;
    },
  ) => api.patch<RiskFinding>(`/reports/findings/${findingId}/review`, payload),

  addContext: (versionId: string, contextData: Record<string, any>) =>
    api.post(`/reports/${versionId}/context`, contextData),

  getDiff: (versionId: string, compareWith: string, reportType: 'report1' | 'report2') =>
    api.get<ReportDiff>(`/reports/${versionId}/diff`, {
      params: { compare_with: compareWith, report_type: reportType }
    }),

  downloadPdf: async (versionId: string, reportType: 'full' | 'report1' | 'report2' = 'full') => {
    const response = await http.get<Blob>(`/reports/${versionId}/download`, {
      params: { type: reportType },
      responseType: 'blob',
    });
    const disposition = response.headers['content-disposition'] as string | undefined;
    const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] || `${reportType === 'full' ? 'rapport-audit-conformite-complet' : reportType}.pdf`;
    return { blob: response.data, filename };
  },

  downloadMarkdown: async (versionId: string, reportType: 'full' | 'report1' | 'report2' = 'full') => {
    const response = await http.get<Blob>(`/reports/${versionId}/export`, {
      params: { format: 'markdown', type: reportType },
      responseType: 'blob',
    });
    const disposition = response.headers['content-disposition'] as string | undefined;
    const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] || `${reportType === 'full' ? 'rapport-audit-conformite-complet' : reportType}.md`;
    return { blob: response.data, filename };
  },
};

// Admin API
export const adminApi = {
  // Sources
  listSources: (params?: { status?: string; country_code?: string; level?: string }) =>
    api.get<LegalSource[]>('/admin/sources', { params }),

  listDocuments: (params?: { parent_id?: string; country_code?: string; level?: string; search?: string }) =>
    api.get<LegalDocumentItem[]>('/admin/sources/documents', { params }),

  createSource: (data: Partial<LegalSource>) =>
    api.post<LegalSource>('/admin/sources', data),

  updateSource: (id: string, data: Partial<LegalSource>) =>
    api.patch<LegalSource>(`/admin/sources/${id}`, data),

  deleteSource: (id: string) =>
    api.delete(`/admin/sources/${id}`),

  verifySource: (id: string) =>
    api.post(`/admin/sources/${id}/verify`),

  collectSource: (id: string, depth: number = 2) =>
    api.post<SourceCollectionRun>(`/admin/sources/${id}/collect`, null, { params: { depth } }),

  listSourceCollections: (id: string) =>
    api.get<SourceCollectionRun[]>(`/admin/sources/${id}/collections`),

  downloadDocumentUrl: (sourceId: string) =>
    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/admin/sources/${sourceId}/download`,

  // Scoring Rules
  listRules: () =>
    api.get('/admin/rules'),

  createRule: (data: any) =>
    api.post('/admin/rules', data),

  updateRule: (id: string, data: any) =>
    api.patch(`/admin/rules/${id}`, data),

  // LLM Configs
  listModels: () =>
    api.get<LLMModelConfig[]>('/admin/models'),
  listModelProviders: () =>
    api.get<LLMProviderAvailability[]>('/admin/models/providers'),

  createModel: (data: any) =>
    api.post<LLMModelConfig>('/admin/models', data),

  updateModel: (id: string, data: any) =>
    api.patch<LLMModelConfig>(`/admin/models/${id}`, data),

  // Countries
  listCountries: () =>
    api.get('/admin/countries'),

  updateCountry: (code: string, data: { is_active: boolean }) =>
    api.patch(`/admin/countries/${code}`, data),

  // Users
  listUsers: () =>
    api.get('/admin/users'),

  createPlatformAdmin: (data: { email: string; password: string }) =>
    api.post('/admin/users/admins', data),

  // Audit Logs
  listAuditLogs: (params?: { entity_type?: string; user_id?: string }) =>
    api.get('/admin/audit', { params }),

  // Regulatory Sentinel Alerts
  listAlerts: (params?: { status?: string; jurisdiction?: string; source_id?: string }) =>
    api.get<RegulatoryAlertItem[]>('/admin/alerts', { params }),

  reviewAlert: (id: string, data: { action: 'approve' | 'dismiss'; note?: string }) =>
    api.post<RegulatoryAlertItem>(`/admin/alerts/${id}/review`, data),
};

// Sovereign Master Corpus Explorer API
export const corpusApi = {
  getSummary: () => api.get<CorpusSummary>('/corpus/summary'),

  listTexts: (jurisdiction?: string) =>
    api.get<LegalTextItem[]>('/corpus/texts', {
      params: jurisdiction ? { jurisdiction } : undefined,
    }),

  listTextSections: (textId: string) =>
    api.get<CorpusSectionItem[]>(`/corpus/texts/${textId}/sections`),

  listArticles: (params?: {
    text_id?: string;
    section_id?: string;
    jurisdiction?: string;
    has_sanction?: boolean;
    compliance_rule_type?: string;
    q?: string;
    mode?: 'keyword' | 'hybrid';
    skip?: number;
    limit?: number;
  }) => api.get<CorpusArticlePage>('/corpus/articles', { params }),

  getArticle: (articleId: string) =>
    api.get<CorpusArticleItem>(`/corpus/articles/${articleId}`),

  downloadPdf: async (textId: string) => {
    const response = await http.get<Blob>(`/corpus/texts/${textId}/pdf`, {
      responseType: 'blob',
    });
    const disposition = response.headers['content-disposition'] as string | undefined;
    const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] || 'texte_officiel.pdf';
    return { blob: response.data, filename };
  },
};
