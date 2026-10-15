import { request } from './client';
import { AssistantRequest, AssistantResponse } from '../types';

export const assistantApi = {
  askAssistant: async (payload: AssistantRequest): Promise<AssistantResponse> => {
    return request<AssistantResponse>('/api/v1/assistant', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
