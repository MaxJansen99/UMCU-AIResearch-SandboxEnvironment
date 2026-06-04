import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, LogOut, RefreshCw, XCircle } from 'lucide-react';
import { AuthUser, authorizationHeaders, clearToken, getStoredToken } from '../utils/authClient';
import { Button } from './ui/button';
import umcLogo from '../../assets/umc_utrecht_Logo_jpg.svg';

type PendingRequest = {
  id: number;
  title: string;
  status: string;
  created_by_user_id: number;
  created_at: string;
  filters_json: Record<string, unknown>;
  items: Array<{
    id: number;
    orthanc_study_id: string;
    study_info?: {
      study_date?: string;
      study_description?: string;
      modalities?: string[];
    } | null;
  }>;
  approval?: {
    decision: string;
    reason: string | null;
  } | null;
  export?: {
    status: 'PENDING' | 'READY' | 'FAILED';
    export_path: string | null;
    manifest_path: string | null;
    error: string | null;
    request_hash: string | null;
    reused_from_export_id: number | null;
  } | null;
};

type DatamanagerPageProps = {
  user: AuthUser;
  onLogout: () => void;
};

export function DatamanagerPage({ user, onLogout }: DatamanagerPageProps) {
  const [requests, setRequests] = useState<PendingRequest[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<PendingRequest | null>(null);
  const [decisionReason, setDecisionReason] = useState('');
  const [decisionMessage, setDecisionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);

  const loadPending = async () => {
    const token = getStoredToken();
    if (!token) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/requests/pending', {
        headers: authorizationHeaders(token),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Pending requests laden mislukt.');
      }
      setRequests(payload.requests || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Pending requests laden mislukt.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPending();
  }, []);

  const logout = () => {
    clearToken();
    onLogout();
  };

  const selectRequest = (request: PendingRequest) => {
    setSelectedRequest(request);
    setDecisionReason('');
    setDecisionError(null);
    setDecisionMessage(null);
  };

  const decide = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!selectedRequest) return;
    if (decision === 'REJECTED' && !decisionReason.trim()) {
      setDecisionError('Reason is verplicht bij reject.');
      return;
    }

    const token = getStoredToken();
    if (!token) return;

    setIsDeciding(true);
    setDecisionError(null);
    setDecisionMessage(null);
    try {
      const response = await fetch(`/api/requests/${selectedRequest.id}/decision`, {
        method: 'POST',
        headers: {
          ...authorizationHeaders(token),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ decision, reason: decisionReason.trim() || null }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || 'Besluit opslaan mislukt.');
      }

      setSelectedRequest(payload.request);
      setDecisionMessage(`Aanvraag #${payload.request.id} is ${payload.request.status}.`);
      setDecisionReason('');
      await loadPending();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Besluit opslaan mislukt.';
      setDecisionError(message);
    } finally {
      setIsDeciding(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-4">
            <img src={umcLogo} alt="UMC Utrecht" className="h-12 w-auto object-contain" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Datamanager</h1>
              <p className="text-sm text-gray-600">{user.username}</p>
            </div>
          </div>
          <Button variant="outline" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Uitloggen
          </Button>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1400px] gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(420px,0.9fr)]">
        <div>
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Pending requests</h2>
              <p className="text-sm text-gray-600">Ingediende selectie-aanvragen wachten hier op besluit.</p>
            </div>
            <Button variant="outline" onClick={loadPending} disabled={isLoading}>
              <RefreshCw className="h-4 w-4" />
              Vernieuwen
            </Button>
          </div>

          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
          )}

          <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-100 text-gray-700">
                  <tr>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Titel</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Studies</th>
                    <th className="px-4 py-3">Aangemaakt</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-gray-600" colSpan={5}>
                        Geen pending requests.
                      </td>
                    </tr>
                  ) : (
                    requests.map((request) => (
                      <tr
                        key={request.id}
                        onClick={() => selectRequest(request)}
                        className={`cursor-pointer border-t border-gray-200 hover:bg-blue-50 ${
                          selectedRequest?.id === request.id ? 'bg-blue-50' : ''
                        }`}
                      >
                        <td className="px-4 py-3">{request.id}</td>
                        <td className="px-4 py-3">{request.title}</td>
                        <td className="px-4 py-3">
                          <span className="rounded bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                            {request.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">{request.items.length}</td>
                        <td className="px-4 py-3">{new Date(request.created_at).toLocaleString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          {!selectedRequest ? (
            <div className="text-sm text-gray-600">Selecteer een request om details te bekijken.</div>
          ) : (
            <div className="space-y-5">
              <div>
                <div className="text-sm text-gray-500">Request #{selectedRequest.id}</div>
                <h2 className="text-xl font-semibold text-gray-900">{selectedRequest.title}</h2>
                <p className="text-sm text-gray-600">
                  Status: <span className="font-medium">{selectedRequest.status}</span>
                </p>
                {selectedRequest.export && (
                  <p className="mt-1 text-sm text-gray-600">
                    Export: <span className="font-medium">{selectedRequest.export.status}</span>
                    {selectedRequest.export.manifest_path ? ` - ${selectedRequest.export.manifest_path}` : ''}
                    {selectedRequest.export.reused_from_export_id
                      ? ` - reused from export #${selectedRequest.export.reused_from_export_id}`
                      : ''}
                  </p>
                )}
              </div>

              {decisionMessage && (
                <div className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                  <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{decisionMessage}</span>
                </div>
              )}

              {decisionError && (
                <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{decisionError}</span>
                </div>
              )}

              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Filters</h3>
                <pre className="max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-800">
                  {JSON.stringify(selectedRequest.filters_json || {}, null, 2)}
                </pre>
              </div>

              <div>
                <h3 className="mb-2 font-semibold text-gray-900">Selected studies</h3>
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-100 text-gray-700">
                      <tr>
                        <th className="px-3 py-2">Orthanc study ID</th>
                        <th className="px-3 py-2">Date</th>
                        <th className="px-3 py-2">Modality</th>
                        <th className="px-3 py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRequest.items.map((item) => (
                        <tr key={item.id} className="border-t border-gray-200">
                          <td className="max-w-[180px] truncate px-3 py-2" title={item.orthanc_study_id}>
                            {item.orthanc_study_id}
                          </td>
                          <td className="px-3 py-2">{formatDicomDate(item.study_info?.study_date)}</td>
                          <td className="px-3 py-2">{item.study_info?.modalities?.join(', ') || '-'}</td>
                          <td className="px-3 py-2">{item.study_info?.study_description || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {selectedRequest.status === 'SUBMITTED' && (
                <div>
                  <label htmlFor="decision-reason" className="mb-1 block text-sm font-medium text-gray-700">
                    Comment / reason
                  </label>
                  <textarea
                    id="decision-reason"
                    value={decisionReason}
                    onChange={(event) => setDecisionReason(event.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Optioneel bij approve, verplicht bij reject"
                  />

                  <div className="mt-3 flex flex-wrap gap-3">
                    <Button onClick={() => decide('APPROVED')} disabled={isDeciding}>
                      <CheckCircle className="h-4 w-4" />
                      Approve
                    </Button>
                    <Button variant="destructive" onClick={() => decide('REJECTED')} disabled={isDeciding}>
                      <XCircle className="h-4 w-4" />
                      Reject
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function formatDicomDate(value: string | undefined): string {
  if (!value || !/^\d{8}$/.test(value)) {
    return '-';
  }
  return `${value.slice(6, 8)}-${value.slice(4, 6)}-${value.slice(0, 4)}`;
}
