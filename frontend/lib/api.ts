/**
 * R.A.E. Control Plane - Frontend API Client
 * 
 * Axios-based HTTP client with automatic JWT token injection from MSAL.
 * Connects Next.js dashboard to FastAPI backend for Registry/Controls/Enforcement.
 * 
 * Features:
 * - Auto-injects Entra ID access tokens in Authorization header
 * - Silent token refresh via MSAL acquireTokenSilent
 * - Centralized error handling with retry logic
 * - Type-safe request/response interfaces
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { PublicClientApplication, AccountInfo } from '@azure/msal-browser';

// Type definitions for API responses
export interface ApiError {
  detail: string;
  status_code: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// Registry types
export interface Workflow {
  id: string;
  name: string;
  description: string;
  workflow_type: 'SEQUENTIAL' | 'PARALLEL' | 'CONDITIONAL';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Capability {
  id: string;
  name: string;
  description: string;
  capability_type: 'DATA_ACCESS' | 'COMPUTE' | 'EXTERNAL_API';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  is_active: boolean;
  created_at: string;
}

export interface Connector {
  id: string;
  name: string;
  description: string;
  connector_type: string;
  config: Record<string, any>;
  is_active: boolean;
  last_health_check: string | null;
}

// Controls types
export interface ControlPolicy {
  id: string;
  name: string;
  description: string;
  policy_type: 'RBAC' | 'TIME_BASED' | 'RATE_LIMIT' | 'DATA_SCOPE';
  rules: Record<string, any>;
  enforcement_level: 'ADVISORY' | 'SOFT' | 'HARD';
  is_active: boolean;
}

export interface KillSwitch {
  id: string;
  name: string;
  description: string;
  switch_type: 'HARD_STOP' | 'DEGRADE';
  scope: 'GLOBAL' | 'WORKFLOW' | 'CAPABILITY';
  is_active: boolean;
  activated_at: string | null;
  activated_by: string | null;
}

export interface BreakGlass {
  id: string;
  justification: string;
  requested_by: string;
  approved_by: string | null;
  expires_at: string;
  is_active: boolean;
  revoked_at: string | null;
}

// Enforcement types
export interface AuditEvent {
  id: string;
  event_type: string;
  actor: string;
  resource_type: string;
  resource_id: string;
  action: string;
  outcome: 'SUCCESS' | 'FAILURE' | 'DENIED';
  details: Record<string, any>;
  previous_hash: string | null;
  event_hash: string;
  created_at: string;
}

export interface EnforcementGate {
  id: string;
  name: string;
  description: string;
  gate_type: 'PRE_EXECUTION' | 'POST_EXECUTION' | 'CONTINUOUS';
  checks: string[];
  is_active: boolean;
}

export interface ChangeRequest {
  id: string;
  title: string;
  description: string;
  change_type: 'CONFIGURATION' | 'DEPLOYMENT' | 'EMERGENCY';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'IMPLEMENTED';
  created_by: string;
  reviewed_by: string | null;
  approved_by: string | null;
  implemented_at: string | null;
  created_at: string;
}

/**
 * Creates Axios instance with base configuration
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
    timeout: 30000, // 30 seconds
    headers: {
      'Content-Type': 'application/json',
    },
  });

  return client;
};

export const apiClient = createApiClient();

/**
 * Configures MSAL token injection interceptor
 * 
 * MUST be called from client components after MSAL initialization.
 * Silently acquires Entra ID access token and adds to Authorization header.
 * 
 * @param msalInstance - Initialized MSAL PublicClientApplication
 * @param scopes - API scopes (e.g., ['api://backend-client-id/access_as_user'])
 */
export const configureMsalInterceptor = (
  msalInstance: PublicClientApplication,
  scopes: string[]
) => {
  apiClient.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      try {
        const account: AccountInfo | null = msalInstance.getActiveAccount();
        
        if (account) {
          // Silent token acquisition (uses refresh token if needed)
          const response = await msalInstance.acquireTokenSilent({
            scopes,
            account,
          });
          
          // Inject JWT bearer token
          config.headers.Authorization = `Bearer ${response.accessToken}`;
          
          console.log('[API Client] Token injected for request:', config.url);
        } else {
          console.warn('[API Client] No active account - request sent without token');
        }
      } catch (error) {
        console.error('[API Client] Token acquisition failed:', error);
        // Continue request without token (backend will return 401)
      }
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for error handling
  apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError<ApiError>) => {
      const originalRequest = error.config;

      // Handle 401 Unauthorized (expired token)
      if (error.response?.status === 401 && originalRequest) {
        console.warn('[API Client] 401 Unauthorized - attempting interactive login');
        
        try {
          const account = msalInstance.getActiveAccount();
          if (account) {
            // Try interactive token acquisition
            const response = await msalInstance.acquireTokenPopup({
              scopes,
              account,
            });
            
            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${response.accessToken}`;
            return apiClient(originalRequest);
          }
        } catch (interactiveError) {
          console.error('[API Client] Interactive login failed:', interactiveError);
        }
      }

      // Log error details for debugging
      console.error('[API Client] Request failed:', {
        url: originalRequest?.url,
        status: error.response?.status,
        detail: error.response?.data?.detail || error.message,
      });

      return Promise.reject(error);
    }
  );
};

// ============================================================================
// API Endpoint Functions
// ============================================================================

// Registry API
export const registryApi = {
  // Workflows
  getWorkflows: (params?: { is_active?: boolean; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<Workflow>>('/registry/workflows', { params }),
  
  getWorkflow: (id: string) =>
    apiClient.get<Workflow>(`/registry/workflows/${id}`),
  
  createWorkflow: (data: Partial<Workflow>) =>
    apiClient.post<Workflow>('/registry/workflows', data),
  
  updateWorkflow: (id: string, data: Partial<Workflow>) =>
    apiClient.put<Workflow>(`/registry/workflows/${id}`, data),
  
  deactivateWorkflow: (id: string) =>
    apiClient.patch<Workflow>(`/registry/workflows/${id}/deactivate`),

  // Capabilities
  getCapabilities: (params?: { risk_level?: string; is_active?: boolean }) =>
    apiClient.get<PaginatedResponse<Capability>>('/registry/capabilities', { params }),
  
  getCapability: (id: string) =>
    apiClient.get<Capability>(`/registry/capabilities/${id}`),
  
  createCapability: (data: Partial<Capability>) =>
    apiClient.post<Capability>('/registry/capabilities', data),

  // Connectors
  getConnectors: (params?: { connector_type?: string; is_active?: boolean }) =>
    apiClient.get<PaginatedResponse<Connector>>('/registry/connectors', { params }),
  
  getConnector: (id: string) =>
    apiClient.get<Connector>(`/registry/connectors/${id}`),
  
  testConnector: (id: string) =>
    apiClient.post<{ status: string; latency_ms: number }>(`/registry/connectors/${id}/test`),
};

// Controls API
export const controlsApi = {
  // Control Policies
  getPolicies: (params?: { policy_type?: string; is_active?: boolean }) =>
    apiClient.get<PaginatedResponse<ControlPolicy>>('/controls/policies', { params }),
  
  getPolicy: (id: string) =>
    apiClient.get<ControlPolicy>(`/controls/policies/${id}`),
  
  createPolicy: (data: Partial<ControlPolicy>) =>
    apiClient.post<ControlPolicy>('/controls/policies', data),

  // Kill Switches
  getKillSwitches: (params?: { is_active?: boolean; scope?: string }) =>
    apiClient.get<PaginatedResponse<KillSwitch>>('/controls/kill-switches', { params }),
  
  getKillSwitch: (id: string) =>
    apiClient.get<KillSwitch>(`/controls/kill-switches/${id}`),
  
  activateKillSwitch: (id: string, data: { reason: string; activated_by: string }) =>
    apiClient.post<KillSwitch>(`/controls/kill-switches/${id}/activate`, data),
  
  deactivateKillSwitch: (id: string) =>
    apiClient.post<KillSwitch>(`/controls/kill-switches/${id}/deactivate`),

  // Break-Glass
  getBreakGlassTokens: (params?: { is_active?: boolean }) =>
    apiClient.get<PaginatedResponse<BreakGlass>>('/controls/break-glass', { params }),
  
  requestBreakGlass: (data: { justification: string; duration_hours: number }) =>
    apiClient.post<BreakGlass>('/controls/break-glass/request', data),
  
  revokeBreakGlass: (id: string) =>
    apiClient.post<BreakGlass>(`/controls/break-glass/${id}/revoke`),
};

// Enforcement API
export const enforcementApi = {
  // Audit Events
  getAuditEvents: (params?: { 
    event_type?: string; 
    actor?: string;
    outcome?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<PaginatedResponse<AuditEvent>>('/enforcement/audit-events', { params }),
  
  getAuditEvent: (id: string) =>
    apiClient.get<AuditEvent>(`/enforcement/audit-events/${id}`),
  
  verifyAuditChain: (params?: { start_date?: string; end_date?: string }) =>
    apiClient.post<{ valid: boolean; verified_count: number; errors: string[] }>(
      '/enforcement/audit-events/verify-chain',
      params
    ),

  // Enforcement Gates
  getGates: (params?: { gate_type?: string; is_active?: boolean }) =>
    apiClient.get<PaginatedResponse<EnforcementGate>>('/enforcement/gates', { params }),
  
  getGate: (id: string) =>
    apiClient.get<EnforcementGate>(`/enforcement/gates/${id}`),

  // Change Requests
  getChangeRequests: (params?: { status?: string; risk_level?: string }) =>
    apiClient.get<PaginatedResponse<ChangeRequest>>('/enforcement/change-requests', { params }),
  
  getChangeRequest: (id: string) =>
    apiClient.get<ChangeRequest>(`/enforcement/change-requests/${id}`),
  
  createChangeRequest: (data: Partial<ChangeRequest>) =>
    apiClient.post<ChangeRequest>('/enforcement/change-requests', data),
  
  reviewChangeRequest: (id: string, data: { decision: 'APPROVED' | 'REJECTED'; comments: string }) =>
    apiClient.post<ChangeRequest>(`/enforcement/change-requests/${id}/review`, data),
  
  implementChangeRequest: (id: string) =>
    apiClient.post<ChangeRequest>(`/enforcement/change-requests/${id}/implement`),
};

// Health check
export const healthApi = {
  getHealth: () =>
    apiClient.get<{ status: string; version: string; timestamp: string }>('/health'),
};

/**
 * Helper function to handle API errors consistently
 */
export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;
    return axiosError.response?.data?.detail || axiosError.message || 'Unknown API error';
  }
  return 'An unexpected error occurred';
};

export default apiClient;
