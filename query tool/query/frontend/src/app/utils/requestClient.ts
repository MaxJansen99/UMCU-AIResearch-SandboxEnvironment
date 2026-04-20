import { authorizationHeaders, getStoredToken } from './authClient';

export type ApprovalInfo = {
  id: number;
  decision: string;
  reason: string | null;
  decided_at: string;
};

export type SelectionRequest = {
  id: number;
  title: string;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';
  filters_json: Record<string, unknown>;
  created_at: string;
  items: Array<{ id: number; orthanc_study_id: string }>;
  approval: ApprovalInfo | null;
};

function authToken(): string {
  const token = getStoredToken();
  if (!token) {
    throw new Error('Niet ingelogd.');
  }
  return token;
}

async function jsonRequest<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || 'Request mislukt.');
  }
  return payload;
}

export async function createSelectionRequest(
  title: string,
  filtersJson: Record<string, unknown>,
): Promise<SelectionRequest> {
  const payload = await jsonRequest<{ request: SelectionRequest }>('/requests', {
    method: 'POST',
    headers: {
      ...authorizationHeaders(authToken()),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, filters_json: filtersJson }),
  });
  return payload.request;
}

export async function addSelectionItems(requestId: number, orthancStudyIds: string[]): Promise<SelectionRequest> {
  const payload = await jsonRequest<{ request: SelectionRequest }>(`/requests/${requestId}/items`, {
    method: 'POST',
    headers: {
      ...authorizationHeaders(authToken()),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ orthanc_study_ids: orthancStudyIds }),
  });
  return payload.request;
}

export async function submitSelectionRequest(requestId: number): Promise<SelectionRequest> {
  const payload = await jsonRequest<{ request: SelectionRequest }>(`/requests/${requestId}/submit`, {
    method: 'POST',
    headers: {
      ...authorizationHeaders(authToken()),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  });
  return payload.request;
}

export async function listMySelectionRequests(): Promise<SelectionRequest[]> {
  const payload = await jsonRequest<{ requests: SelectionRequest[] }>('/requests/mine', {
    headers: authorizationHeaders(authToken()),
  });
  return payload.requests;
}
