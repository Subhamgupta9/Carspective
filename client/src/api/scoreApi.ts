import { request } from './client';
import { ScoreResponse } from '../types';

export interface ScorePayload {
  brand: string;
  model: string;
  manufacturing_year?: number;
  fuel_type?: string;
  transmission_type?: string;
  variant?: string;
}

export const scoreApi = {
  getScore: async (payload: ScorePayload): Promise<ScoreResponse> => {
    return request<ScoreResponse>('/api/v1/score', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
