import { Filter, Plus, Minus } from 'lucide-react';
import { DicomStats, FilterConfig, analyzeHeader } from '../utils/dicomLoader';
import { formatHeaderLabel } from '../utils/formatters';
import { useState, useMemo, useEffect } from 'react';

interface DynamicFiltersProps {
  stats: DicomStats | null;
  activeFilters: Array<{ header: string; value: any }>;
  onFiltersChange: (filters: Array<{ header: string; value: any }>) => void;
  onSearch: (filters?: Array<{ header: string; value: any }>) => void;
  isLoading: boolean;
}

export function DynamicFilters({ 
  stats, 
  activeFilters, 
  onFiltersChange, 
  onSearch, 
  isLoading 
}: DynamicFiltersProps) {
  // Get the core metadata headers from stats dynamically.
  const defaultHeaders = useMemo(() => {
    if (!stats) return [];
    return Object.keys(stats.stats).slice(0, 5);
  }, [stats]);

  const [selectedHeaders, setSelectedHeaders] = useState<string[]>([]);

  // Update selectedHeaders when stats loads
  useEffect(() => {
    if (defaultHeaders.length > 0 && selectedHeaders.length === 0) {
      setSelectedHeaders(defaultHeaders);
    }
  }, [defaultHeaders, selectedHeaders.length]);

  const availableHeaders = useMemo(() => {
    if (!stats) return [];
    return Object.keys(stats.stats).sort();
  }, [stats]);

  const filterConfigs = useMemo(() => {
    if (!stats) return new Map<string, FilterConfig>();
    
    const configs = new Map<string, FilterConfig>();
    for (const [header, values] of Object.entries(stats.stats)) {
      configs.set(header, analyzeHeader(header, values));
    }
    return configs;
  }, [stats]);

  const addFilterHeader = () => {
    const unusedHeaders = availableHeaders.filter(h => !selectedHeaders.includes(h));
    if (unusedHeaders.length > 0) {
      setSelectedHeaders([...selectedHeaders, unusedHeaders[0]]);
    }
  };

  const removeFilterHeader = (header: string) => {
    setSelectedHeaders(selectedHeaders.filter(h => h !== header));
    // Also remove from active filters
    onFiltersChange(activeFilters.filter(f => f.header !== header));
  };

  const updateFilter = (header: string, value: any) => {
    const existing = activeFilters.filter(f => f.header !== header);
    const isEmptyObject =
      typeof value === 'object' &&
      value !== null &&
      value.min === undefined &&
      value.max === undefined;

    if (value !== undefined && value !== '' && value !== null && !isEmptyObject) {
      onFiltersChange([...existing, { header, value }]);
    } else {
      onFiltersChange(existing);
    }
  };

  const getFilterValue = (header: string) => {
    const filter = activeFilters.find(f => f.header === header);
    return filter?.value;
  };

  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-center text-gray-500">Loading filters...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold text-gray-900">Filter Controls</h2>
        </div>
        <button
          onClick={addFilterHeader}
          className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100"
        >
          <Plus className="w-4 h-4" />
          Add Filter
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {selectedHeaders.map(header => {
          const config = filterConfigs.get(header);
          if (!config) return null;

          const currentValue = getFilterValue(header);

          return (
            <div key={header} className="relative">
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  {formatHeaderLabel(header)}
                </label>
                <button
                  onClick={() => removeFilterHeader(header)}
                  className="text-gray-400 hover:text-red-500"
                  title="Remove filter"
                >
                  <Minus className="w-4 h-4" />
                </button>
              </div>

              {header === 'StudyDate' && (
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    min="2000-01-01"
                    aria-label="Study date from"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    value={toDateInputValue(currentValue?.min)}
                    onChange={(e) => {
                      const min = toDicomDate(e.target.value);
                      updateFilter(header, { ...currentValue, min });
                    }}
                  />
                  <input
                    type="date"
                    min="2000-01-01"
                    aria-label="Study date to"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    value={toDateInputValue(currentValue?.max)}
                    onChange={(e) => {
                      const max = toDicomDate(e.target.value);
                      updateFilter(header, { ...currentValue, max });
                    }}
                  />
                </div>
              )}

              {header !== 'StudyDate' && config.type === 'categorical' && (
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  value={currentValue || ''}
                  onChange={(e) => updateFilter(header, e.target.value || undefined)}
                >
                  <option value="">All</option>
                  {config.values.map(val => (
                    <option key={val} value={val}>
                      {val || '(empty)'}
                    </option>
                  ))}
                </select>
              )}

              {header !== 'StudyDate' && config.type === 'text' && (
                <input
                  type="text"
                  placeholder={`Search ${header}...`}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  value={currentValue || ''}
                  onChange={(e) => updateFilter(header, e.target.value || undefined)}
                />
              )}

              {header !== 'StudyDate' && config.type === 'numeric' && (
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="Min"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    value={currentValue?.min ?? ''}
                    onChange={(e) => {
                      const val = e.target.value ? parseFloat(e.target.value) : undefined;
                      updateFilter(header, { ...currentValue, min: val });
                    }}
                  />
                  <input
                    type="number"
                    placeholder="Max"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                    value={currentValue?.max ?? ''}
                    onChange={(e) => {
                      const val = e.target.value ? parseFloat(e.target.value) : undefined;
                      updateFilter(header, { ...currentValue, max: val });
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={() => onSearch()}
          disabled={isLoading}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
        >
          <Filter className="w-4 h-4" />
          {isLoading ? 'Searching...' : 'Apply Filters'}
        </button>
        <button
          onClick={() => {
            onFiltersChange([]);
            onSearch([]);
          }}
          className="px-6 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
        >
          Clear All
        </button>
      </div>

      {activeFilters.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-sm text-gray-600">
            Active filters: {activeFilters.length}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {activeFilters.map((filter, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded"
              >
                {formatHeaderLabel(filter.header)}: {typeof filter.value === 'object' 
                  ? `${filter.value.min || '∞'} - ${filter.value.max || '∞'}`
                  : filter.value}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function toDicomDate(value: string): string | undefined {
  return value ? value.replace(/-/g, '') : undefined;
}

function toDateInputValue(value: unknown): string {
  const rawValue = String(value || '');
  if (!/^\d{8}$/.test(rawValue)) {
    return '';
  }
  return `${rawValue.slice(0, 4)}-${rawValue.slice(4, 6)}-${rawValue.slice(6, 8)}`;
}
