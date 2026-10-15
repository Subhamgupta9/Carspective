import { request } from './client';
import { RecommendationResponse, UserProfile, ListingContext } from '../types';

export interface RecommendationPayload {
  brand: string;
  model: string;
  manufacturing_year?: number;
  fuel_type?: string;
  transmission_type?: string;
  city?: string;
  variant?: string;
  listing?: ListingContext;
  user_profile?: UserProfile;
}

export const recommendationApi = {
  getRecommendation: async (payload: RecommendationPayload): Promise<RecommendationResponse> => {
    return request<RecommendationResponse>('/api/v1/recommendation', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
