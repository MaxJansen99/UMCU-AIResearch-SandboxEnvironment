import { useState, useEffect } from 'react';
import { DynamicFilters } from './components/DynamicFilters';
import { DynamicTable } from './components/DynamicTable';
import { DynamicStatsPanel } from './components/DynamicStatsPanel';
import { DatamanagerPage } from './components/DatamanagerPage';
import { LoginPage } from './components/LoginPage';
import { 
  DicomInstance, 
  DicomStats, 
  loadDicomStats, 
  generateInstancesFromStats,
  DynamicFilters as DynamicFiltersType
} from './utils/dicomLoader';
import { AuthUser, clearToken, getStoredToken, me, routeForRole } from './utils/authClient';
import { queryOrthancMetadata } from './utils/queryClient';
import {
  addSelectionItems,
  createSelectionRequest,
  listMySelectionRequests,
  SelectionRequest,
  submitSelectionRequest,
} from './utils/requestClient';
import { CheckCircle, Send, AlertCircle, LogOut } from 'lucide-react';
import huLogo from '../assets/hogeschool_utrecht_Logo_jpg.png';
import umcLogo from '../assets/umc_utrecht_Logo_jpg.svg';

export default function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const path = window.location.pathname;
      const token = getStoredToken();

      if (!token) {
        setIsCheckingAuth(false);
        if (path !== '/login') {
          window.location.replace('/login');
        }
        return;
      }

      try {
        const user = await me(token);
        const expectedRoute = routeForRole(user.role);
        if (path === '/' || path === '/dashboard' || path === '/login' || path !== expectedRoute) {
          window.location.replace(expectedRoute);
          return;
        }
        setAuthUser(user);
      } catch {
        clearToken();
        if (path !== '/login') {
          window.location.replace('/login');
          return;
        }
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogout = () => {
    clearToken();
    setAuthUser(null);
    window.location.assign('/login');
  };

  if (isCheckingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-sm text-gray-600">Sessie controleren...</div>
      </div>
    );
  }

  if (window.location.pathname === '/login') {
    return <LoginPage />;
  }

  if (!authUser) {
    return null;
  }

  if (window.location.pathname === '/datamanager') {
    return <DatamanagerPage user={authUser} onLogout={handleLogout} />;
  }

  return <ResearcherDashboard user={authUser} onLogout={handleLogout} />;
}

type ResearcherDashboardProps = {
  user: AuthUser;
  onLogout: () => void;
};

function ResearcherDashboard({ user, onLogout }: ResearcherDashboardProps) {
  const [stats, setStats] = useState<DicomStats | null>(null);
  const [allInstances, setAllInstances] = useState<DicomInstance[]>([]);
  const [filteredInstances, setFilteredInstances] = useState<DicomInstance[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedStudyIdsBySeriesId, setSelectedStudyIdsBySeriesId] = useState<Map<string, string>>(new Map());
  const [activeFilters, setActiveFilters] = useState<Array<{ header: string; value: any }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [requestTitle, setRequestTitle] = useState('');
  const [myRequests, setMyRequests] = useState<SelectionRequest[]>([]);
  const [requestMessage, setRequestMessage] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isSubmittingRequest, setIsSubmittingRequest] = useState(false);
  const pageSize = 25;

  // Load stats on mount
  useEffect(() => {
    loadData();
    loadMyRequests();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const loadedStats = await loadDicomStats();
      setStats(loadedStats);
      
      // Generate instances from the stats
      const instances = generateInstancesFromStats(loadedStats);
      setAllInstances(instances);
      setFilteredInstances(instances);
    } catch (error) {
      console.error('Error loading DICOM stats:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setLoadError(`Failed to load DICOM statistics: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (filtersToApply = activeFilters) => {
    if (!stats) return;
    
    setIsLoading(true);
    setCurrentPage(0);
    
    // Convert activeFilters to DynamicFiltersType format
    const filters: DynamicFiltersType = {};
    
    for (const filter of filtersToApply) {
      const { header, value } = filter;
      
      // Determine filter type
      if (typeof value === 'object' && (value.min !== undefined || value.max !== undefined)) {
        // Numeric range filter
        filters[header] = {
          type: 'numeric',
          min: value.min,
          max: value.max
        };
      } else if (typeof value === 'string') {
        // Could be categorical or text - check if it's an exact match or search
        const headerValues = stats.stats[header];
        if (headerValues && headerValues[value] !== undefined) {
          // Exact categorical match
          filters[header] = {
            type: 'categorical',
            value: value
          };
        } else {
          // Text search
          filters[header] = {
            type: 'text',
            value: value
          };
        }
      }
    }
    
    try {
      const result = await queryOrthancMetadata(filters);
      setStats(result.stats);
      setAllInstances(result.instances);
      setFilteredInstances(result.instances);
    } catch (error) {
      console.error('Error querying DICOM metadata:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setLoadError(`Failed to query DICOM metadata: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMyRequests = async () => {
    try {
      setMyRequests(await listMySelectionRequests());
    } catch (error) {
      console.error('Error loading selection requests:', error);
    }
  };

  const handleSelectionChange = (nextSelectedIds: Set<string>) => {
    const visibleStudyIdsBySeriesId = new Map(
      filteredInstances.map((instance) => [instance.id, getOrthancStudyId(instance)]),
    );

    setSelectedIds(nextSelectedIds);
    setSelectedStudyIdsBySeriesId((current) => {
      const next = new Map(current);
      for (const [seriesId, studyId] of visibleStudyIdsBySeriesId.entries()) {
        if (nextSelectedIds.has(seriesId)) {
          next.set(seriesId, studyId);
        } else {
          next.delete(seriesId);
        }
      }
      return next;
    });
  };

  const handleSubmitForApproval = async () => {
    const orthancStudyIds = uniqueValues(Array.from(selectedStudyIdsBySeriesId.values()));
    if (orthancStudyIds.length === 0) {
      setRequestError('Selecteer minimaal een study.');
      setRequestMessage(null);
      return;
    }

    setIsSubmittingRequest(true);
    setRequestError(null);
    setRequestMessage(null);

    try {
      const title = requestTitle.trim() || `Selectie ${new Date().toLocaleString()}`;
      const created = await createSelectionRequest(title, {
        active_filters: activeFilters,
        selected_study_count: orthancStudyIds.length,
      });
      await addSelectionItems(created.id, orthancStudyIds);
      const submitted = await submitSelectionRequest(created.id);
      setRequestMessage(`Aanvraag #${submitted.id} is verstuurd met status ${submitted.status}.`);
      setSelectedIds(new Set());
      setSelectedStudyIdsBySeriesId(new Map());
      setRequestTitle('');
      await loadMyRequests();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Aanvraag versturen mislukt.';
      setRequestError(message);
    } finally {
      setIsSubmittingRequest(false);
    }
  };

  const selectedInstances = filteredInstances.filter(i => selectedIds.has(i.id));
  const selectedStudyCount = uniqueValues(Array.from(selectedStudyIdsBySeriesId.values())).length;
  const resultStudyCount = uniqueValues(filteredInstances.map(getOrthancStudyId)).length;

  const allHeaders = stats ? [...Object.keys(stats.stats), 'Images'] : [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="relative max-w-[1600px] mx-auto px-6 py-4 sm:px-40 text-center">
          <img
            src={umcLogo}
            alt="UMC Utrecht"
            className="mx-auto mb-3 h-12 w-auto object-contain sm:absolute sm:left-6 sm:top-1/2 sm:mb-0 sm:h-16 sm:-translate-y-1/2"
          />
          <h1 className="text-2xl font-bold text-gray-900">DICOM Metadata Query Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">
            Search Orthanc metadata from the DICOM archive
            {stats && (
              <span className="ml-2 text-blue-600">
                • {stats.total_instances || 0} images • {stats.total_series || 0} series
                {stats.timestamp && (
                  <span className="text-gray-500">
                    {' '}• Updated: {new Date(stats.timestamp * 1000).toLocaleString()}
                  </span>
                )}
              </span>
            )}
          </p>
          <div className="mt-3 flex items-center justify-center gap-3 sm:absolute sm:right-6 sm:top-1/2 sm:mt-0 sm:-translate-y-1/2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-500">Made by</span>
            <img src={huLogo} alt="Hogeschool Utrecht" className="h-12 w-auto object-contain sm:h-24" />
          </div>
          <div className="mt-3 flex items-center justify-center gap-3">
            <span className="text-xs text-gray-600">{user.username}</span>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100"
            >
              <LogOut className="h-4 w-4" />
              Uitloggen
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-6 py-6 space-y-6">
        {/* Error State */}
        {loadError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Data</h3>
              <p className="text-sm text-red-700 mt-1">{loadError}</p>
              <button
                onClick={loadData}
                className="mt-2 px-4 py-1 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && !stats && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-600">Loading DICOM statistics...</p>
          </div>
        )}

        {/* Main Content */}
        {stats && (
          <>
            {/* Filter Controls */}
            <DynamicFilters
              stats={stats}
              activeFilters={activeFilters}
              onFiltersChange={setActiveFilters}
              onSearch={handleSearch}
              isLoading={isLoading}
            />

            {/* Results Info */}
            {filteredInstances.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-blue-900">
                    {activeFilters.length > 0 ? (
                      <>
                        Found <strong>{filteredInstances.length}</strong> series across {resultStudyCount} studies matching {activeFilters.length} filter(s)
                        {selectedIds.size > 0 && (
                          <span> • <strong>{selectedIds.size}</strong> selected series across {selectedStudyCount} studies</span>
                        )}
                      </>
                    ) : (
                      <>
                        Showing all <strong>{filteredInstances.length}</strong> series across {resultStudyCount} studies
                        {selectedIds.size > 0 && (
                          <span> • <strong>{selectedIds.size}</strong> selected series across {selectedStudyCount} studies</span>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Results Table */}
            <DynamicTable
              instances={filteredInstances}
              allHeaders={allHeaders}
              selectedIds={selectedIds}
              onSelectionChange={handleSelectionChange}
              currentPage={currentPage}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
            />

            {/* Action Buttons */}
            {filteredInstances.length > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex flex-col gap-3 md:flex-row md:items-end">
                  <div className="flex-1">
                    <label htmlFor="request-title" className="mb-1 block text-sm font-medium text-gray-700">
                      Aanvraag titel
                    </label>
                    <input
                      id="request-title"
                      type="text"
                      value={requestTitle}
                      onChange={(event) => setRequestTitle(event.target.value)}
                      placeholder="Bijvoorbeeld: MRI hersenen april"
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleSubmitForApproval}
                    disabled={isSubmittingRequest || selectedIds.size === 0}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
                  >
                    <Send className="h-4 w-4" />
                    {isSubmittingRequest ? 'Versturen...' : 'Submit for approval'}
                  </button>
                </div>

                <div className="mt-3 text-sm text-gray-600">
                  {selectedIds.size} geselecteerde series uit {selectedStudyCount} stud{selectedStudyCount === 1 ? 'y' : "y's"}
                </div>

                {requestMessage && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                    <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{requestMessage}</span>
                  </div>
                )}

                {requestError && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <span>{requestError}</span>
                  </div>
                )}
              </div>
            )}

            <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-900">Mijn aanvragen</h2>
                  <p className="text-sm text-gray-600">Status van je selectie-aanvragen.</p>
                </div>
                <button
                  type="button"
                  onClick={loadMyRequests}
                  className="rounded-md border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Vernieuwen
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-gray-700">
                    <tr>
                      <th className="px-3 py-2">ID</th>
                      <th className="px-3 py-2">Titel</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Studies</th>
                      <th className="px-3 py-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {myRequests.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-gray-600" colSpan={5}>
                          Nog geen aanvragen.
                        </td>
                      </tr>
                    ) : (
                      myRequests.map((request) => (
                        <tr key={request.id} className="border-t border-gray-200">
                          <td className="px-3 py-2">{request.id}</td>
                          <td className="px-3 py-2">{request.title}</td>
                          <td className="px-3 py-2">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${statusClass(request.status)}`}>
                              {request.status}
                            </span>
                          </td>
                          <td className="px-3 py-2">{request.items.length}</td>
                          <td className="px-3 py-2 text-gray-700">{request.approval?.reason || '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Statistics Panel */}
            {filteredInstances.length > 0 && (
              <DynamicStatsPanel
                instances={filteredInstances}
                selectedInstances={selectedInstances}
                allHeaders={allHeaders}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

function getOrthancStudyId(instance: DicomInstance): string {
  return String(instance.OrthancStudyID || instance.StudyInstanceUID || instance.id);
}

function uniqueValues(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function statusClass(status: SelectionRequest['status']): string {
  if (status === 'APPROVED') return 'bg-green-100 text-green-700';
  if (status === 'REJECTED') return 'bg-red-100 text-red-700';
  if (status === 'SUBMITTED') return 'bg-blue-100 text-blue-700';
  return 'bg-gray-100 text-gray-700';
}
