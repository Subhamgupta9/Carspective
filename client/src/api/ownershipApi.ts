import { request } from './client';
import {
  VehicleOwnershipIntelligence,
  FuelCostRequest,
  FuelCostResponse,
  TCOCalculationRequest,
  TCOCalculationResponse,
} from '../types';

export const ownershipApi = {
  getOwnershipIntelligence: async (canonicalId: string): Promise<VehicleOwnershipIntelligence> => {
    return request<VehicleOwnershipIntelligence>(`/api/v1/ownership/${encodeURIComponent(canonicalId)}`);
  },

  calculateFuelCost: async (payload: FuelCostRequest): Promise<FuelCostResponse> => {
    return request<FuelCostResponse>('/api/v1/ownership/cost', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  calculateTCO: async (payload: TCOCalculationRequest): Promise<TCOCalculationResponse> => {
    return request<TCOCalculationResponse>('/api/v1/ownership/tco', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
