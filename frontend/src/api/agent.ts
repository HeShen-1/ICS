import { request } from './client';

interface DecomposeTask {
  id: number;
  service: string;
  description: string;
  dependencies: number[];
}

interface DecomposeResponse {
  services: string[];
  tasks: DecomposeTask[];
  parallel_groups: number[][];
  explanation: string;
}

export type { DecomposeTask, DecomposeResponse };

export async function decomposeRequirement(requirement: string): Promise<DecomposeResponse> {
  return request('/agent/decompose', {
    method: 'POST',
    body: JSON.stringify({ requirement }),
  });
}
