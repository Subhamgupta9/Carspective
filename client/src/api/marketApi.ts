import { request } from './client';
import {
  VehicleMarketProfile,
  DepreciationProfile,
  SegmentBenchmark,
  CurrentMarketIntelligenceResponse,
  CurrentPriceDistribution,
  CurrentMarketSupply,
  CurrentRegionalIntelligence,
  CurrentMarketEvidence,
  CurrentMarketIngestionResult,
} from '../types';

export const marketApi = {
  // Phase 14 Historical Empirical Endpoints
  getMarketProfile: async (canonicalId: string): Promise<VehicleMarketProfile> => {
    return request<VehicleMarketProfile>(`/api/v1/market/${encodeURIComponent(canonicalId)}`);
  },

  getDepreciationTrends: async (canonicalId: string): Promise<DepreciationProfile> => {
    return request<DepreciationProfile>(`/api/v1/market/${encodeURIComponent(canonicalId)}/trends`);
  },

  getSegmentBenchmark: async (canonicalId: string): Promise<SegmentBenchmark> => {
    return request<SegmentBenchmark>(`/api/v1/market/${encodeURIComponent(canonicalId)}/segment`);
  },

  // Phase 17 Current Market Observations & Intelligence Endpoints
  getCurrentMarketIntelligence: async (canonicalId: string): Promise<CurrentMarketIntelligenceResponse> => {
    return request<CurrentMarketIntelligenceResponse>(`/api/v1/market/current/${encodeURIComponent(canonicalId)}`);
  },

  getCurrentPriceDistribution: async (canonicalId: string): Promise<CurrentPriceDistribution> => {
    return request<CurrentPriceDistribution>(`/api/v1/market/current/${encodeURIComponent(canonicalId)}/distribution`);
  },

  getCurrentSupply: async (canonicalId: string): Promise<CurrentMarketSupply> => {
    return request<CurrentMarketSupply>(`/api/v1/market/current/${encodeURIComponent(canonicalId)}/supply`);
  },

  getCurrentRegional: async (canonicalId: string): Promise<CurrentRegionalIntelligence[]> => {
    return request<CurrentRegionalIntelligence[]>(`/api/v1/market/current/${encodeURIComponent(canonicalId)}/regional`);
  },

  getCurrentEvidence: async (canonicalId: string): Promise<CurrentMarketEvidence> => {
    return request<CurrentMarketEvidence>(`/api/v1/market/current/${encodeURIComponent(canonicalId)}/evidence`);
  },

  ingestMarketRecords: async (
    records?: any[],
    adminApiKey: string = 'carspective-admin-phase17-key'
  ): Promise<CurrentMarketIngestionResult> => {
    return request<CurrentMarketIngestionResult>('/api/v1/market/admin/ingest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Api-Key': adminApiKey,
      },
      body: JSON.stringify(records ? { records } : {}),
    });
  },
};
