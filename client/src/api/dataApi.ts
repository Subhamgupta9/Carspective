import { request } from './client';
import {
  GovernedSource,
  DomainFreshnessSummary,
  DataQualityReport,
  EvidenceLineageNode,
} from '../types';

export const dataApi = {
  getSources: async (status: string = 'ACTIVE', type?: string): Promise<GovernedSource[]> => {
    const params = new URLSearchParams({ status });
    if (type) params.append('type', type);
    return request<GovernedSource[]>(`/api/v1/data/sources?${params.toString()}`);
  },

  getSource: async (sourceId: string): Promise<GovernedSource & { freshness_policy?: any }> => {
    return request<GovernedSource & { freshness_policy?: any }>(`/api/v1/data/sources/${encodeURIComponent(sourceId)}`);
  },

  getFreshness: async (): Promise<DomainFreshnessSummary[]> => {
    return request<DomainFreshnessSummary[]>('/api/v1/data/freshness');
  },

  getQuality: async (): Promise<DataQualityReport> => {
    return request<DataQualityReport>('/api/v1/data/quality');
  },

  getClaimLineage: async (claimId: string): Promise<EvidenceLineageNode> => {
    return request<EvidenceLineageNode>(`/api/v1/data/lineage/${encodeURIComponent(claimId)}`);
  },

  getEvidenceLineage: async (evidenceId: string): Promise<any> => {
    return request<any>(`/api/v1/data/evidence/${encodeURIComponent(evidenceId)}`);
  },
};
