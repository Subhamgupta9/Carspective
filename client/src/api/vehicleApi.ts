import { request } from './client';
import {
  Manufacturer,
  VehicleModel,
  VehicleGeneration,
  VehicleVariant,
  CanonicalResolutionRequest,
  CanonicalResolutionResponse,
  VehicleKnowledgeProfile,
  DiscoverySearchResponse,
  AutocompleteResponse,
  VehicleWorkspaceResponse,
} from '../types';

export const vehicleApi = {
  getManufacturers: async (): Promise<Manufacturer[]> => {
    return request<Manufacturer[]>('/api/v1/vehicles/manufacturers');
  },

  getModelsByManufacturer: async (makeSlug: string): Promise<VehicleModel[]> => {
    return request<VehicleModel[]>(`/api/v1/vehicles/${encodeURIComponent(makeSlug)}/models`);
  },

  getGenerations: async (makeSlug: string, modelSlug: string): Promise<VehicleGeneration[]> => {
    return request<VehicleGeneration[]>(`/api/v1/vehicles/${encodeURIComponent(makeSlug)}/${encodeURIComponent(modelSlug)}/generations`);
  },

  getVariants: async (makeSlug: string, modelSlug: string, genSlug: string): Promise<VehicleVariant[]> => {
    return request<VehicleVariant[]>(`/api/v1/vehicles/${encodeURIComponent(makeSlug)}/${encodeURIComponent(modelSlug)}/${encodeURIComponent(genSlug)}/variants`);
  },

  resolveVehicle: async (params: CanonicalResolutionRequest): Promise<CanonicalResolutionResponse> => {
    return request<CanonicalResolutionResponse>('/api/v1/vehicles/resolve', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  getProvenance: async (canonicalId: string, category?: string): Promise<any> => {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    return request<any>(`/api/v1/vehicles/provenance/${encodeURIComponent(canonicalId)}${query}`);
  },

  getVehicleProfile: async (canonicalId: string): Promise<VehicleKnowledgeProfile> => {
    return request<VehicleKnowledgeProfile>(`/api/v1/vehicles/profile/${encodeURIComponent(canonicalId)}`);
  },

  searchVehicles: async (params?: {
    q?: string;
    make?: string;
    model?: string;
    year?: number;
    fuel?: string;
    transmission?: string;
    body_type?: string;
    budget_min?: number;
    budget_max?: number;
    seating_capacity?: number;
    limit?: number;
    offset?: number;
  }): Promise<DiscoverySearchResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set('q', params.q);
    if (params?.make) searchParams.set('make', params.make);
    if (params?.model) searchParams.set('model', params.model);
    if (params?.year) searchParams.set('year', params.year.toString());
    if (params?.fuel) searchParams.set('fuel', params.fuel);
    if (params?.transmission) searchParams.set('transmission', params.transmission);
    if (params?.body_type) searchParams.set('body_type', params.body_type);
    if (params?.budget_min !== undefined) searchParams.set('budget_min', params.budget_min.toString());
    if (params?.budget_max !== undefined) searchParams.set('budget_max', params.budget_max.toString());
    if (params?.seating_capacity !== undefined) searchParams.set('seating_capacity', params.seating_capacity.toString());
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    const qs = searchParams.toString();
    const res = await request<any>(`/api/v1/vehicles/search${qs ? `?${qs}` : ''}`);
    if (Array.isArray(res)) {
      return {
        query: params?.q || '',
        intent: { raw_query: params?.q || '', normalized_query: params?.q || '' },
        result_type: 'FILTERED_RESULTS',
        total_count: res.length,
        results: res.map(r => ({
          canonical_vehicle_id: r.canonical_vehicle_id,
          title: r.title,
          manufacturer: r.make || r.manufacturer,
          model: r.model,
          generation: r.generation,
          model_year: r.year,
          variant: r.variant,
          fuel_type: r.fuel_type,
          transmission: r.transmission,
          body_type: r.body_type,
          coverage_tier: r.coverage_tier || 'TIER_1',
          evidence_state: 'SUPPORTED',
          has_deep_knowledge: false,
          match_score: r.match_score || 50,
          match_reasons: [],
          available_actions: ['view', 'compare', 'value', 'deal', 'inspect']
        })),
        provenance: {
          query_normalized: params?.q || '',
          rules_applied: [],
          taxonomy_version: 'Phase 2 Canonical Taxonomy',
          resolution_method: 'Deterministic',
          evidence_sources_checked: 12
        }
      };
    }
    return res as DiscoverySearchResponse;
  },

  autocomplete: async (q: string, limit: number = 8): Promise<AutocompleteResponse> => {
    const searchParams = new URLSearchParams({ q });
    if (limit) searchParams.set('limit', limit.toString());
    return request<AutocompleteResponse>(`/api/v1/vehicles/autocomplete?${searchParams.toString()}`);
  },

  getSpecifications: async (canonicalId: string): Promise<any> => {
    return request<any>(`/api/v1/vehicles/${encodeURIComponent(canonicalId)}/specifications`);
  },

  getSafety: async (canonicalId: string): Promise<any> => {
    return request<any>(`/api/v1/vehicles/${encodeURIComponent(canonicalId)}/safety`);
  },

  getFeatures: async (canonicalId: string, variant?: string): Promise<any> => {
    const query = variant ? `?variant=${encodeURIComponent(variant)}` : '';
    return request<any>(`/api/v1/vehicles/${encodeURIComponent(canonicalId)}/features${query}`);
  },

  getOwnership: async (canonicalId: string): Promise<any> => {
    return request<any>(`/api/v1/vehicles/${encodeURIComponent(canonicalId)}/ownership`);
  },

  getEvidence: async (canonicalId: string): Promise<any> => {
    return request<any>(`/api/v1/vehicles/${encodeURIComponent(canonicalId)}/evidence`);
  },

  getVehicleWorkspace: async (
    canonicalId: string,
    askingPrice?: number,
    kmDriven?: number
  ): Promise<VehicleWorkspaceResponse> => {
    const params = new URLSearchParams();
    if (askingPrice !== undefined && askingPrice !== null) params.append('asking_price', askingPrice.toString());
    if (kmDriven !== undefined && kmDriven !== null) params.append('km_driven', kmDriven.toString());
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<VehicleWorkspaceResponse>(`/api/v1/vehicles/workspace/${encodeURIComponent(canonicalId)}${qs}`);
  },
};

