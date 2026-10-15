import { request } from './client';
import { InspectionEvaluationResponse } from '../types';

export interface InspectionPayload {
  brand: string;
  model: string;
  manufacturing_year?: number;
  fuel_type?: string;
  transmission_type?: string;
  variant?: string;
  odometer_km?: number;
  asking_price?: number;
  custom_findings?: Array<{
    item_id: string;
    status: 'PASS' | 'ATTENTION' | 'FAIL' | 'UNKNOWN' | 'NOT_APPLICABLE';
    source?: string;
    notes?: string;
  }>;
}

export const inspectionApi = {
  getInspection: async (payload: InspectionPayload): Promise<InspectionEvaluationResponse> => {
    return request<InspectionEvaluationResponse>('/api/v1/inspection', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
