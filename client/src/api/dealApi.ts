import { request } from './client';
import { DealAnalysisRequest, DealAnalysisResponse } from '../types';

export const dealApi = {
  analyzeDeal: async (payload: DealAnalysisRequest): Promise<DealAnalysisResponse> => {
    return request<DealAnalysisResponse>('/api/v1/deal-analysis', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
