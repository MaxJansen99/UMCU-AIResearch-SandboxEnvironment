import { ChevronDown, Filter } from 'lucide-react';
import { DicomStats, FilterConfig, analyzeHeader } from '../utils/dicomLoader';
import { formatHeaderLabel } from '../utils/formatters';
import { useMemo, useState } from 'react';

interface DynamicFiltersProps {
  stats: DicomStats | null;
  activeFilters: Array<{ header: string; value: any }>;
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
  BodyPartExamined: [
    { value: 'BRAIN', label: 'Brain' },
    { value: 'CHEST', label: 'Chest' },
    { value: 'ABDOMEN', label: 'Abdomen' },
    { value: 'PELVIS', label: 'Pelvis' },
    { value: 'SPINE', label: 'Spine' },
    { value: 'HEART', label: 'Cardiac' },
    { value: 'BREAST', label: 'Breast' },
    { value: 'EXTREMITY', label: 'Extremity' },
    { value: 'VASCULAR', label: 'Vascular' },
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
              <span key={value || '__unknown__'} className="px-2 py-1 rounded bg-blue-50 text-blue-700 text-xs">
                {getOptionLabel(options, value)}
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
    const statsConfig = filterConfigs.get(header);
    const config = getPresetFilterConfig(header, statsConfig) || statsConfig;
    if (!config) return null;

    const currentValue = getFilterValue(header);

    if (header === 'StudyDate') {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-gray-600">From date</span>
            <input
              type="date"
              min="1900-01-01"
              aria-label="Study date from"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={toDateInputValue(currentValue?.min)}
              onChange={(event) => {
                const min = toDicomDate(event.target.value);
                updateFilter(header, { ...currentValue, min });
              }}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-gray-600">To date</span>
            <input
              type="date"
              min="1900-01-01"
              aria-label="Study date to"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              value={toDateInputValue(currentValue?.max)}
              onChange={(event) => {
                const max = toDicomDate(event.target.value);
                updateFilter(header, { ...currentValue, max });
              }}
            />
          </label>
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
                    x
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    if (config.type === 'categorical') {
      return renderCategoricalFilter(header, getCategoricalOptions(header, config, stats.stats[header] || {}));
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

          return (
            <section key={section.id}>
              <button
                type="button"
                onClick={() => toggleSection(section.id)}
                className={`flex w-full items-center justify-between border-b border-gray-200 px-4 py-3 text-left transition-colors ${
                  isOpen ? 'bg-gray-100' : 'bg-gray-50 hover:bg-gray-100'
                }`}
              >
                <span className="font-medium text-gray-900">{section.title}</span>
                <ChevronDown
                  className={`h-4 w-4 text-gray-500 transition-transform ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

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

function formatActiveFilterValue(value: any): string {
  if (Array.isArray(value)) {
    return value
      .map(item => {
        if (typeof item === 'object' && item !== null && item.min !== undefined && item.max !== undefined) {
          return `${item.min}-${item.max}`;
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

    return options;
  }

  return config.values.map(value => ({
    value,
    label: value || 'Unknown',
    count: counts[value] || 0,
  }));
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
