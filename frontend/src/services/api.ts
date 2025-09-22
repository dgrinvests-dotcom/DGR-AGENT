import axios from 'axios';
import { Campaign, Lead, Conversation, DashboardStats, LeadImportResult, IntegrationStatus, ApiResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dashboard API
export const dashboardApi = {
  getStats: (): Promise<DashboardStats> =>
    api.get('/api/dashboard/stats').then(res => res.data),
  
  getIntegrationStatus: (): Promise<IntegrationStatus> =>
    api.get('/api/dashboard/integrations').then(res => res.data),
};

// Campaign API
export const campaignApi = {
  getAll: (): Promise<Campaign[]> =>
    api.get('/api/campaigns').then(res => res.data),
  
  getById: (id: string): Promise<Campaign> =>
    api.get(`/api/campaigns/${id}`).then(res => res.data),
  
  create: (campaign: Partial<Campaign>): Promise<Campaign> =>
    api.post('/api/campaigns', campaign).then(res => res.data),
  
  update: (id: string, campaign: Partial<Campaign>): Promise<Campaign> =>
    api.put(`/api/campaigns/${id}`, campaign).then(res => res.data),
  
  delete: (id: string): Promise<ApiResponse<any>> =>
    api.delete(`/api/campaigns/${id}`).then(res => res.data),
  
  start: (id: string): Promise<ApiResponse<any>> =>
    api.post(`/api/campaigns/${id}/start`).then(res => res.data),
  
  pause: (id: string): Promise<ApiResponse<any>> =>
    api.post(`/api/campaigns/${id}/pause`).then(res => res.data),
  
  stop: (id: string): Promise<ApiResponse<any>> =>
    api.post(`/api/campaigns/${id}/stop`).then(res => res.data),

  execute: (id: string): Promise<ApiResponse<any>> =>
    api.post(`/api/campaigns/${id}/execute`).then(res => res.data),

  getExecutionStatus: (id: string): Promise<any> =>
    api.get(`/api/campaigns/${id}/status`).then(res => res.data),
};

// Lead API
export const leadApi = {
  getAll: (params?: { 
    campaign_id?: string; 
    status?: string; 
    property_type?: string;
    page?: number;
    limit?: number;
  }): Promise<{ leads: Lead[]; total: number }> =>
    api.get('/api/leads', { params }).then(res => res.data),
  
  getById: (id: string): Promise<Lead> =>
    api.get(`/api/leads/${id}`).then(res => res.data),
  
  create: (lead: Partial<Lead>): Promise<Lead> =>
    api.post('/api/leads', lead).then(res => res.data),
  
  update: (id: string, lead: Partial<Lead>): Promise<Lead> =>
    api.put(`/api/leads/${id}`, lead).then(res => res.data),
  
  delete: (id: string): Promise<ApiResponse<any>> =>
    api.delete(`/api/leads/${id}`).then(res => res.data),
  
  import: (file: File, campaignId: string): Promise<LeadImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('campaign_id', campaignId);
    
    return api.post('/api/leads/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(res => res.data);
  },
  
  export: (campaignId: string, format: 'csv' | 'xlsx' = 'csv'): Promise<Blob> =>
    api.get(`/api/leads/export/${campaignId}`, {
      params: { format },
      responseType: 'blob'
    }).then(res => res.data),
};

// Conversation API
export const conversationApi = {
  getAll: (params?: {
    lead_id?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<{ conversations: Conversation[]; total: number }> =>
    api.get('/api/conversations', { params }).then(res => res.data),
  
  getById: (id: string): Promise<Conversation> =>
    api.get(`/api/conversations/${id}`).then(res => res.data),
  
  getByLeadId: (leadId: string): Promise<Conversation[]> =>
    api.get(`/api/conversations/lead/${leadId}`).then(res => res.data),
  
  sendMessage: (leadId: string, message: string): Promise<ApiResponse<any>> =>
    api.post(`/api/conversations/${leadId}/message`, { message }).then(res => res.data),
};

// Analytics API
export const analyticsApi = {
  getCampaignPerformance: (campaignId: string, period: string = '7d'): Promise<any> =>
    api.get(`/api/analytics/campaigns/${campaignId}`, { params: { period } }).then(res => res.data),
  
  getConversionFunnel: (campaignId?: string): Promise<any> =>
    api.get('/api/analytics/funnel', { params: { campaign_id: campaignId } }).then(res => res.data),
  
  getResponseRates: (period: string = '30d'): Promise<any> =>
    api.get('/api/analytics/response-rates', { params: { period } }).then(res => res.data),
};

export default api;
