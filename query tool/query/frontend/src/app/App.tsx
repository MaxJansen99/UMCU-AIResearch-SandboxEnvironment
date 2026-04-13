import { useState, useEffect } from 'react';
import { DynamicFilters } from './components/DynamicFilters';
import { DynamicTable } from './components/DynamicTable';
import { DynamicStatsPanel } from './components/DynamicStatsPanel';
import { 
  DicomInstance, 
  DicomStats, 
  loadDicomStats, 
  generateInstancesFromStats,
  DynamicFilters as DynamicFiltersType
} from './utils/dicomLoader';
import { queryOrthancMetadata } from './utils/queryClient';
import { Download, Send, AlertCircle } from 'lucide-react';

export default function App() {
  const [stats, setStats] = useState<DicomStats | null>(null);
  const [allInstances, setAllInstances] = useState<DicomInstance[]>([]);
  const [filteredInstances, setFilteredInstances] = useState<DicomInstance[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeFilters, setActiveFilters] = useState<Array<{ header: string; value: any }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 25;

  // Load stats on mount
  useEffect(() => {
    loadData();
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

  const handleSearch = async () => {
    if (!stats) return;
    
    setIsLoading(true);
    setCurrentPage(0);
    
    // Convert activeFilters to DynamicFiltersType format
    const filters: DynamicFiltersType = {};
    
    for (const filter of activeFilters) {
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
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Error querying DICOM metadata:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      setLoadError(`Failed to query DICOM metadata: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const selectedInstances = filteredInstances.filter(i => selectedIds.has(i.id));

  const allHeaders = stats ? [...Object.keys(stats.stats), 'Instances'] : [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">DICOM Metadata Query Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">
            Search Orthanc metadata from the DICOM archive
            {stats && (
              <span className="ml-2 text-blue-600">
                • {stats.total_instances || 0} instances • {stats.total_series || 0} series
                {stats.timestamp && (
                  <span className="text-gray-500">
                    {' '}• Updated: {new Date(stats.timestamp * 1000).toLocaleString()}
                  </span>
                )}
              </span>
            )}
          </p>
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
                        Found <strong>{filteredInstances.length}</strong> instances matching {activeFilters.length} filter(s)
                        {selectedIds.size > 0 && (
                          <span> • <strong>{selectedIds.size}</strong> selected</span>
                        )}
                      </>
                    ) : (
                      <>
                        Showing all <strong>{filteredInstances.length}</strong> instances
                        {selectedIds.size > 0 && (
                          <span> • <strong>{selectedIds.size}</strong> selected</span>
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
              onSelectionChange={setSelectedIds}
              currentPage={currentPage}
              pageSize={pageSize}
              onPageChange={setCurrentPage}
            />

            {/* Action Buttons */}
            {filteredInstances.length > 0 && (
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  aria-label="Inactive action"
                  title="No action configured."
                  className="flex items-center justify-center px-6 py-2 bg-green-600 text-white rounded-md cursor-default transition-colors"
                >
                  <Download className="w-4 h-4" />
                </button>
                
                <button
                  type="button"
                  aria-label="Inactive action"
                  title="No action configured."
                  className="flex items-center justify-center px-6 py-2 bg-purple-600 text-white rounded-md cursor-default transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            )}

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
