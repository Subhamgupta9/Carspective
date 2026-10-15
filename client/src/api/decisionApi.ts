import { request } from './client';
import {
  UserRequirementsProfile,
  NaturalLanguageRequirementsResponse,
  DecisionEvaluationResponse,
  ShortlistRankResponse,
  PersonalizedComparisonResponse,
  PersonalizedInspectionPrioritizationResponse,
} from '../types';

export const decisionApi = {
  parseQuery: async (query: string): Promise<NaturalLanguageRequirementsResponse> => {
    return request<NaturalLanguageRequirementsResponse>('/api/v1/decision/parse-query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  },

  evaluateVehicle: async (
    canonicalVehicleId: string,
    profile: UserRequirementsProfile,
    askingPrice?: number,
    kmDriven?: number
  ): Promise<DecisionEvaluationResponse> => {
    return request<DecisionEvaluationResponse>('/api/v1/decision/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        canonical_vehicle_id: canonicalVehicleId,
        profile,
        asking_price: askingPrice,
        km_driven: kmDriven,
      }),
    });
  },

  rankShortlist: async (
    canonicalIds: string[],
    profile: UserRequirementsProfile
  ): Promise<ShortlistRankResponse> => {
    return request<ShortlistRankResponse>('/api/v1/decision/rank', {
      method: 'POST',
      body: JSON.stringify({
        canonical_ids: canonicalIds,
        profile,
      }),
    });
  },

  compareVehicles: async (
    canonicalIds: string[],
    profile: UserRequirementsProfile
  ): Promise<PersonalizedComparisonResponse> => {
    return request<PersonalizedComparisonResponse>('/api/v1/decision/compare', {
      method: 'POST',
      body: JSON.stringify({
        canonical_ids: canonicalIds,
        profile,
      }),
    });
  },

  prioritizeInspection: async (
    canonicalVehicleId: string,
    profile: UserRequirementsProfile
  ): Promise<PersonalizedInspectionPrioritizationResponse> => {
    return request<PersonalizedInspectionPrioritizationResponse>('/api/v1/decision/prioritize-inspection', {
      method: 'POST',
      body: JSON.stringify({
        canonical_vehicle_id: canonicalVehicleId,
        profile,
      }),
    });
  },
};
