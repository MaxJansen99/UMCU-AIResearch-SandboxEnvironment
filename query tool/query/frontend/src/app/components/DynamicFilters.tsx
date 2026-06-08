import { ChevronDown, Filter, X } from 'lucide-react';
import { DicomStats, FilterConfig, analyzeHeader } from '../utils/dicomLoader';
import { formatHeaderLabel } from '../utils/formatters';
import { useMemo, useState, useEffect, useRef } from 'react';

interface DynamicFiltersProps {
  stats: DicomStats | null;
  activeFilters: Array<{ header: string; value: any }>;
  statsExcludingSelf: Record<string, Record<string, number>>;
  onFiltersChange: (filters: Array<{ header: string; value: any }>) => void;
  onSearch: (filters?: Array<{ header: string; value: any }>) => void;
  isLoading: boolean;
}

type FilterOption = {
  value: string;
  label: string;
  count?: number;
  disabled?: boolean;
};

type AgeRange = {
  min: number;
  max: number;
};

type DateRange = {
  min: string;
  max: string;
};

const PRESET_FILTER_OPTIONS: Record<string, FilterOption[]> = {
  Modality: [
    { value: 'MR', label: 'MRI' },
    { value: 'CT', label: 'CT' },
    { value: 'US', label: 'Ultrasound' },
    { value: 'XR', label: 'X-ray' },
    { value: 'PT', label: 'PET' },
    { value: 'NM', label: 'Nuclear medicine' },
  ],
  PatientSex: [
    { value: 'M', label: 'Male' },
    { value: 'F', label: 'Female' },
    { value: 'O', label: 'Other' },
    { value: '', label: 'Unknown' },
  ],
};

const FILTER_SECTIONS = [
  {
    id: 'modality',
    title: 'Modality',
    headers: ['Modality'],
    defaultOpen: true,
  },
  {
    id: 'bodyPart',
    title: 'Body Part',
    headers: ['BodyPartExamined'],
    defaultOpen: false,
  },
  {
    id: 'studyDate',
    title: 'Study Date',
    headers: ['StudyDate'],
    defaultOpen: false,
  },
  {
    id: 'patient',
    title: 'Patient',
    headers: ['PatientBirthDate', 'PatientSex'],
    defaultOpen: false,
  },
] as const;

export function DynamicFilters({
  stats,
  statsExcludingSelf,
  activeFilters,
  onFiltersChange,
  onSearch,
  isLoading
}: DynamicFiltersProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(
    Object.fromEntries(FILTER_SECTIONS.map(section => [section.id, section.defaultOpen]))
  );
  const [bodyPartSearch, setBodyPartSearch] = useState('');
  const [ageRangeDraft, setAgeRangeDraft] = useState({ min: '', max: '' });
  const [studyDateRangeDraft, setStudyDateRangeDraft] = useState({ min: '', max: '' });
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastActiveFiltersRef = useRef<string>('');

  // Auto-search with debouncing when filters change (for cascading filter updates)
  useEffect(() => {
    const serializedFilters = JSON.stringify(activeFilters);
    if (serializedFilters === lastActiveFiltersRef.current) {
      return;
    }

    lastActiveFiltersRef.current = serializedFilters;

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      onSearch(activeFilters);
    }, 300); // 300ms debounce

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [activeFilters, onSearch]);

  const filterConfigs = useMemo(() => {
    if (!stats) return new Map<string, FilterConfig>();

    const configs = new Map<string, FilterConfig>();
    for (const [header, values] of Object.entries(stats.stats)) {
      configs.set(header, analyzeHeader(header, values));
    }
    return configs;
  }, [stats]);

  const availableHeaders = useMemo(() => {
    if (!stats) return new Set<string>();
    return new Set(Object.keys(stats.stats));
  }, [stats]);

  const updateFilter = (header: string, value: any) => {
    const existing = activeFilters.filter(f => f.header !== header);
    const isEmptyArray = Array.isArray(value) && value.length === 0;
    const isEmptyObject =
      !Array.isArray(value) &&
      typeof value === 'object' &&
      value !== null &&
      value.min === undefined &&
      value.max === undefined;

    if (value !== undefined && value !== '' && value !== null && !isEmptyObject && !isEmptyArray) {
      onFiltersChange([...existing, { header, value }]);
    } else {
      onFiltersChange(existing);
    }
  };

  const getFilterValue = (header: string) => {
    const filter = activeFilters.find(f => f.header === header);
    return filter?.value;
  };

  const getHeaderStatsForRendering = (header: string): Record<string, number> => {
    const fallbackStats = stats?.stats?.[header] || {};
    const hasHeaderFilter = activeFilters.some(filter => filter.header === header);
    if (!hasHeaderFilter) {
      return fallbackStats;
    }

    return statsExcludingSelf?.[header] || fallbackStats;
  };

  const toggleCategoricalValue = (header: string, option: string) => {
    const currentValue = getFilterValue(header);
    const selectedValues = Array.isArray(currentValue)
      ? currentValue
      : currentValue
        ? [String(currentValue)]
        : [];
    const nextValues = selectedValues.includes(option)
      ? selectedValues.filter(value => value !== option)
      : [...selectedValues, option];

    updateFilter(header, nextValues);
  };

  const toggleSection = (sectionId: string) => {
    setOpenSections(current => ({
      ...current,
      [sectionId]: !current[sectionId],
    }));
  };

  const addAgeRange = () => {
    const min = Number(ageRangeDraft.min);
    const max = Number(ageRangeDraft.max);
    if (!Number.isFinite(min) || !Number.isFinite(max) || min < 0 || max < 0 || min > max) {
      return;
    }

    const currentValue = getFilterValue('PatientBirthDate');
    const currentRanges: AgeRange[] = Array.isArray(currentValue) ? currentValue : [];
    const alreadyExists = currentRanges.some(range => range.min === min && range.max === max);
    if (!alreadyExists) {
      updateFilter('PatientBirthDate', [...currentRanges, { min, max }]);
    }
    setAgeRangeDraft({ min: '', max: '' });
  };

  const removeAgeRange = (indexToRemove: number) => {
    const currentValue = getFilterValue('PatientBirthDate');
    const currentRanges: AgeRange[] = Array.isArray(currentValue) ? currentValue : [];
    updateFilter(
      'PatientBirthDate',
      currentRanges.filter((_, index) => index !== indexToRemove)
    );
  };

  const addStudyDateRange = () => {
    const min = toDicomDate(studyDateRangeDraft.min);
    const max = toDicomDate(studyDateRangeDraft.max);
    if (!min || !max || min > max) {
      return;
    }

    const currentValue = getFilterValue('StudyDate');
    const currentRanges: DateRange[] = Array.isArray(currentValue) ? currentValue : [];
    const alreadyExists = currentRanges.some(range => range.min === min && range.max === max);
    if (!alreadyExists) {
      updateFilter('StudyDate', [...currentRanges, { min, max }]);
    }
    setStudyDateRangeDraft({ min: '', max: '' });
  };

  const removeStudyDateRange = (indexToRemove: number) => {
    const currentValue = getFilterValue('StudyDate');
    const currentRanges: DateRange[] = Array.isArray(currentValue) ? currentValue : [];
    updateFilter(
      'StudyDate',
      currentRanges.filter((_, index) => index !== indexToRemove)
    );
  };

  const removeFilter = (header: string) => {
    onFiltersChange(activeFilters.filter(filter => filter.header !== header));
  };

  const resetSection = (headers: readonly string[]) => {
    onFiltersChange(activeFilters.filter(filter => !headers.includes(filter.header)));
  };

  const sectionActiveCount = (headers: readonly string[]) => {
    return activeFilters.filter(filter => headers.includes(filter.header)).length;
  };

  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-center text-gray-500">Loading filters...</div>
      </div>
    );
  }

  const renderCategoricalFilter = (header: string, options: FilterOption[]) => {
    const currentValue = getFilterValue(header);
    const selectedValues = Array.isArray(currentValue)
      ? currentValue
      : currentValue
        ? [String(currentValue)]
        : [];

    const visibleOptions = header === 'BodyPartExamined'
      ? options.filter(option => {
          const search = bodyPartSearch.trim().toLowerCase();
          return !search || option.label.toLowerCase().includes(search) || option.value.toLowerCase().includes(search);
        })
      : options;

    return (
      <div className="space-y-2">
        {header === 'BodyPartExamined' && (
          <input
            type="search"
            placeholder="Search body part..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            value={bodyPartSearch}
            onChange={(event) => setBodyPartSearch(event.target.value)}
          />
        )}

        {selectedValues.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {selectedValues.map(value => (
              <span
                key={value || '__unknown__'}
                className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
              >
                {getOptionLabel(options, value)}
                <button
                  type="button"
                  onClick={() => toggleCategoricalValue(header, value)}
                  className="text-blue-500 hover:text-blue-800"
                  aria-label={`Remove ${getOptionLabel(options, value)} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="max-h-44 overflow-y-auto rounded-md border border-gray-300 bg-white p-2">
          {visibleOptions.length > 0 ? (
            visibleOptions.map(option => (
              <label
                key={option.value || '__unknown__'}
                className={`flex items-center justify-between gap-2 rounded px-1 py-1 text-sm ${
                  option.disabled
                    ? 'cursor-not-allowed text-gray-400'
                    : 'cursor-pointer hover:bg-gray-50'
                }`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!option.disabled && selectedValues.includes(option.value)}
                    disabled={option.disabled}
                    onChange={() => toggleCategoricalValue(header, option.value)}
                    className="rounded border-gray-300"
                  />
                  <span className="truncate">{option.label}</span>
                </span>
                {option.count !== undefined && (
                  <span className="shrink-0 text-xs text-gray-500">{option.count}</span>
                )}
              </label>
            ))
          ) : (
            <div className="px-1 py-2 text-sm text-gray-500">No body parts found.</div>
          )}
        </div>
      </div>
    );
  };

  const renderFilterControl = (header: string) => {
    const headerStats = getHeaderStatsForRendering(header);
    const statsConfig = analyzeHeader(header, headerStats);
    const config = getPresetFilterConfig(header, statsConfig) || statsConfig;
    if (!config) return null;

    const currentValue = getFilterValue(header);

    if (header === 'BodyPartExamined') {
      return renderCategoricalFilter(
        header,
        getCategoricalOptions(header, { ...config, type: 'categorical' }, headerStats)
      );
    }

    if (header === 'StudyDate') {
      const currentValue = getFilterValue(header);
      const selectedRanges: DateRange[] = Array.isArray(currentValue) ? currentValue : [];
      const min = toDicomDate(studyDateRangeDraft.min);
      const max = toDicomDate(studyDateRangeDraft.max);
      const canAddStudyDateRange = Boolean(min && max && min <= max);

      return (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">From date</span>
              <input
                type="date"
                min="1900-01-01"
                aria-label="Study date from"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                value={studyDateRangeDraft.min}
                onChange={(event) => setStudyDateRangeDraft(current => ({ ...current, min: event.target.value }))}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">To date</span>
              <input
                type="date"
                min="1900-01-01"
                aria-label="Study date to"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                value={studyDateRangeDraft.max}
                onChange={(event) => setStudyDateRangeDraft(current => ({ ...current, max: event.target.value }))}
              />
            </label>
            <button
              type="button"
              onClick={addStudyDateRange}
              disabled={!canAddStudyDateRange}
              className="self-end rounded-md bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
            >
              Add range
            </button>
          </div>

          {selectedRanges.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedRanges.map((range, index) => (
                <span
                  key={`${range.min}-${range.max}-${index}`}
                  className="inline-flex items-center gap-2 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
                >
                  {formatDateRange(range)}
                  <button
                    type="button"
                    onClick={() => removeStudyDateRange(index)}
                    className="text-blue-500 hover:text-blue-800"
                    aria-label={`Remove study date range ${formatDateRange(range)}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (header === 'PatientBirthDate') {
      const currentValue = getFilterValue(header);
      const selectedRanges: AgeRange[] = Array.isArray(currentValue) ? currentValue : [];
      const min = Number(ageRangeDraft.min);
      const max = Number(ageRangeDraft.max);
      const canAddAgeRange =
        Number.isFinite(min) &&
        Number.isFinite(max) &&
        min >= 0 &&
        max >= 0 &&
        min <= max;

      return (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">From age</span>
              <input
                type="number"
                min="0"
                aria-label="From age"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                value={ageRangeDraft.min}
                onChange={(event) => setAgeRangeDraft(current => ({ ...current, min: event.target.value }))}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-gray-600">To age</span>
              <input
                type="number"
                min="0"
                aria-label="To age"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                value={ageRangeDraft.max}
                onChange={(event) => setAgeRangeDraft(current => ({ ...current, max: event.target.value }))}
              />
            </label>
            <button
              type="button"
              onClick={addAgeRange}
              disabled={!canAddAgeRange}
              className="self-end rounded-md bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-400"
            >
              Add range
            </button>
          </div>

          {selectedRanges.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedRanges.map((range, index) => (
                <span
                  key={`${range.min}-${range.max}-${index}`}
                  className="inline-flex items-center gap-2 rounded bg-blue-50 px-2 py-1 text-xs text-blue-700"
                >
                  {range.min}-{range.max}
                  <button
                    type="button"
                    onClick={() => removeAgeRange(index)}
                    className="text-blue-500 hover:text-blue-800"
                    aria-label={`Remove age range ${range.min}-${range.max}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (config.type === 'categorical') {
      const headerStats = getHeaderStatsForRendering(header);
      return renderCategoricalFilter(header, getCategoricalOptions(header, config, headerStats));
    }

    if (config.type === 'text') {
      return (
        <input
          type="text"
          placeholder={`Search ${formatHeaderLabel(header)}...`}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          value={currentValue || ''}
          onChange={(event) => updateFilter(header, event.target.value || undefined)}
        />
      );
    }

    if (config.type === 'numeric') {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input
            type="number"
            placeholder="Min"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            value={currentValue?.min ?? ''}
            onChange={(event) => {
              const val = event.target.value ? parseFloat(event.target.value) : undefined;
              updateFilter(header, { ...currentValue, min: val });
            }}
          />
          <input
            type="number"
            placeholder="Max"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            value={currentValue?.max ?? ''}
            onChange={(event) => {
              const val = event.target.value ? parseFloat(event.target.value) : undefined;
              updateFilter(header, { ...currentValue, max: val });
            }}
          />
        </div>
      );
    }

    return null;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-blue-600" />
        <h2 className="font-semibold text-gray-900">Filter Controls</h2>
      </div>

      <div className="divide-y divide-gray-200 rounded-md border border-gray-200">
        {FILTER_SECTIONS.map(section => {
          const sectionHeaders = section.headers.filter(header => availableHeaders.has(header));
          if (sectionHeaders.length === 0) return null;
          const isOpen = openSections[section.id];
          const activeCount = sectionActiveCount(section.headers);

          return (
            <section key={section.id}>
              <div
                className={`flex w-full items-center justify-between border-b border-gray-200 px-4 py-3 text-left transition-colors ${
                  isOpen ? 'bg-gray-100' : 'bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <button
                  type="button"
                  onClick={() => toggleSection(section.id)}
                  className="flex flex-1 items-center justify-between text-left"
                >
                  <span className="font-medium text-gray-900">
                    {section.title}
                    {activeCount > 0 && (
                      <span className="ml-2 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                        {activeCount}
                      </span>
                    )}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 text-gray-500 transition-transform ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {activeCount > 0 && (
                  <button
                    type="button"
                    onClick={() => resetSection(section.headers)}
                    className="ml-3 inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 hover:text-gray-900"
                    aria-label={`Reset ${section.title} filters`}
                  >
                    <X className="h-3 w-3" />
                    Reset
                  </button>
                )}
              </div>

              {isOpen && (
                <div className="space-y-4 bg-white px-4 py-4">
                  {sectionHeaders.map(header => (
                    <div key={header}>
                      {sectionHeaders.length > 1 && (
                        <label className="mb-1 block text-sm font-medium text-gray-700">
                          {formatHeaderLabel(header)}
                        </label>
                      )}
                      {renderFilterControl(header)}
                    </div>
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>

      <div className="sticky bottom-0 -mx-6 mt-6 flex flex-col gap-3 border-t border-gray-200 bg-white/95 px-6 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-gray-600">Active filters: {activeFilters.length}</div>
        <div className="flex gap-3">
          <button
            onClick={() => {
              onFiltersChange([]);
              onSearch([]);
            }}
            className="px-6 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
          >
            Clear All
          </button>
          <button
            onClick={() => onSearch()}
            disabled={isLoading}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
          >
            <Filter className="w-4 h-4" />
            {isLoading ? 'Searching...' : 'Apply Filters'}
          </button>
        </div>
      </div>

      {activeFilters.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {activeFilters.map((filter, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded"
              >
                {formatHeaderLabel(filter.header)}: {formatActiveFilterValue(filter.value)}
                <button
                  type="button"
                  onClick={() => removeFilter(filter.header)}
                  className="ml-1 rounded text-blue-500 hover:text-blue-900"
                  aria-label={`Remove ${formatHeaderLabel(filter.header)} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
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

function formatDateRange(range: DateRange): string {
  return `${formatDicomDate(range.min)} - ${formatDicomDate(range.max)}`;
}

function formatDicomDate(value: unknown): string {
  const rawValue = String(value || '');
  if (!/^\d{8}$/.test(rawValue)) {
    return rawValue;
  }
  return `${rawValue.slice(0, 4)}-${rawValue.slice(4, 6)}-${rawValue.slice(6, 8)}`;
}

function formatActiveFilterValue(value: any): string {
  if (Array.isArray(value)) {
    return value
      .map(item => {
        if (typeof item === 'object' && item !== null && item.min !== undefined && item.max !== undefined) {
          const min = String(item.min);
          const max = String(item.max);
          const isDateRange = /^\d{8}$/.test(min) && /^\d{8}$/.test(max);
          return isDateRange ? `${formatDicomDate(min)} - ${formatDicomDate(max)}` : `${item.min}-${item.max}`;
        }
        return String(item);
      })
      .join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return `${value.min || 'any'} - ${value.max || 'any'}`;
  }
  return String(value);
}

function getOptionLabel(options: FilterOption[], value: string): string {
  return options.find(option => option.value === value)?.label || value || 'Unknown';
}

function getCategoricalOptions(
  header: string,
  config: FilterConfig,
  counts: Record<string, number>
): FilterOption[] {
  const presetOptions = PRESET_FILTER_OPTIONS[header];
  if (presetOptions) {
    const dataValues = new Set(config.values);
    const presetValues = new Set(presetOptions.map(option => option.value));
    const options: FilterOption[] = presetOptions.map(option => ({
      ...option,
      count: counts[option.value] || 0,
      disabled: !dataValues.has(option.value),
    }));

    for (const value of config.values) {
      if (!presetValues.has(value)) {
        options.push({
          value,
          label: value || 'Unknown',
          count: counts[value] || 0,
        });
      }
    }

    // Sort: enabled options by count (descending), then disabled options
    return options.sort((a, b) => {
      const aDisabled = a.disabled ? 1 : 0;
      const bDisabled = b.disabled ? 1 : 0;
      
      // First, sort by disabled status (enabled first)
      if (aDisabled !== bDisabled) {
        return aDisabled - bDisabled;
      }
      
      // Then, sort by count descending (highest first)
      const countDiff = (b.count || 0) - (a.count || 0);
      if (countDiff !== 0) {
        return countDiff;
      }
      
      // Finally, sort alphabetically
      return a.label.localeCompare(b.label);
    });
  }

  return config.values
    .map(value => ({
      value,
      label: value || 'Unknown',
      count: counts[value] || 0,
    }))
    .sort((a, b) => {
      // Sort by count descending (highest first)
      const countDiff = (b.count || 0) - (a.count || 0);
      if (countDiff !== 0) {
        return countDiff;
      }
      // Then by label alphabetically
      return a.label.localeCompare(b.label);
    });
}

function getPresetFilterConfig(header: string, statsConfig?: FilterConfig): FilterConfig | undefined {
  const presetOptions = PRESET_FILTER_OPTIONS[header];
  if (!presetOptions) {
    return undefined;
  }

  return {
    headerName: header,
    values: statsConfig?.values || presetOptions.map(option => option.value),
    type: 'categorical',
  };
}
