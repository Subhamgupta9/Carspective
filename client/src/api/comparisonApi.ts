import { request } from './client';
import { ComparisonResponse, ComparisonVehicleInput, UserProfile } from '../types';

export interface ComparisonPayload {
  vehicles: ComparisonVehicleInput[];
  mode?: 'general' | 'personalized';
  user_profile?: UserProfile;
}

export const comparisonApi = {
  compareVehicles: async (payload: ComparisonPayload): Promise<ComparisonResponse> => {
    return request<ComparisonResponse>('/api/v1/compare', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
