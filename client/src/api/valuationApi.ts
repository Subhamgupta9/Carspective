import { request } from './client';
import { ValuationRequest, ValuationResponse } from '../types';

export const valuationApi = {
  getValuation: async (payload: ValuationRequest): Promise<ValuationResponse> => {
    return request<ValuationResponse>('/api/v1/valuation', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
