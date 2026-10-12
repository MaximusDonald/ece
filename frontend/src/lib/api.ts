import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add auth token
api.interceptors.request.use(
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
api.interceptors.response.use(
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
          
          return api(originalRequest);
        }
      } catch {
        // Refresh failed, redirect to login
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

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

export interface Organization {
  id: string;
  name: string;
  plan: string;
  created_at: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  country_code: string;
  sector: string;
  treatments: string[];
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

export interface RiskFinding {
  id: string;
  report_version_id: string;
  clause_ref: string;
  finding_text: string;
  risk_level: string;
  confidence: string;
  matched_sources: string[];
  obsolescence_flag: boolean;
  conflict_flag: boolean;
  conflict_details: string | null;
  recommendation: string;
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
}

export interface JobResponse {
  job_id: string;
  status: string;
  steps: JobStep[];
  estimated_remaining_seconds: number | null;
  result: Record<string, any> | null;
  error: string | null;
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
  embedding: number[];
  created_at: string;
  updated_at: string;
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
    api.post('/auth/jwt/login', { username: email, password }),
  
  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password }),
  
  logout: () =>
    api.post('/auth/jwt/logout'),
  
  getMe: () =>
    api.get<User>('/auth/users/me'),
  
  updateMe: (data: Partial<User>) =>
    api.patch<User>('/auth/users/me', data),
};

// Organization API
export const orgApi = {
  create: (name: string) =>
    api.post<Organization>('/projects/organization', { name }),
  
  getMe: () =>
    api.get<Organization>('/projects/organization/me'),
};

// Project API
export const projectApi = {
  list: (status?: string) =>
    api.get<ProjectListItem[]>('/projects', { params: { status } }),
  
  create: (data: { name: string; country_code: string; sector: string; treatments: string[] }) =>
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
  
  getJobStatus: (projectId: string, jobId: string) =>
    api.get<JobResponse>(`/projects/${projectId}/documents/jobs/${jobId}`),
};

// Report API
export const reportApi = {
  listVersions: (projectId: string) =>
    api.get<ReportVersionListItem[]>(`/reports/projects/${projectId}`),
  
  getVersion: (versionId: string) =>
    api.get<ReportVersion>(`/reports/${versionId}`),
  
  getFindings: (versionId: string, filters?: { risk_level?: string; confidence?: string }) =>
    api.get<RiskFinding[]>(`/reports/${versionId}/findings`, { params: filters }),
  
  addContext: (versionId: string, contextData: Record<string, any>) =>
    api.post(`/reports/${versionId}/context`, contextData),
  
  getDiff: (versionId: string, compareWith: string, reportType: 'report1' | 'report2') =>
    api.get<ReportDiff>(`/reports/${versionId}/diff`, { 
      params: { compare_with: compareWith, report_type: reportType } 
    }),
};

// Admin API
export const adminApi = {
  // Sources
  listSources: (params?: { status?: string; country_code?: string; level?: string }) =>
    api.get<LegalSource[]>('/admin/sources', { params }),
  
  createSource: (data: Partial<LegalSource>) =>
    api.post<LegalSource>('/admin/sources', data),
  
  updateSource: (id: string, data: Partial<LegalSource>) =>
    api.patch<LegalSource>(`/admin/sources/${id}`, data),
  
  verifySource: (id: string) =>
    api.post(`/admin/sources/${id}/verify`),
  
  // Scoring Rules
  listRules: () =>
    api.get('/admin/rules'),
  
  createRule: (data: any) =>
    api.post('/admin/rules', data),
  
  updateRule: (id: string, data: any) =>
    api.patch(`/admin/rules/${id}`, data),
  
  // LLM Configs
  listModels: () =>
    api.get('/admin/models'),
  
  createModel: (data: any) =>
    api.post('/admin/models', data),
  
  updateModel: (id: string, data: any) =>
    api.patch(`/admin/models/${id}`, data),
  
  // Countries
  listCountries: () =>
    api.get('/admin/countries'),
  
  updateCountry: (code: string, data: { is_active: boolean }) =>
    api.patch(`/admin/countries/${code}`, data),
  
  // Users
  listUsers: () =>
    api.get('/admin/users'),
  
  // Audit Logs
  listAuditLogs: (params?: { entity_type?: string; user_id?: string }) =>
    api.get('/admin/audit', { params }),
};