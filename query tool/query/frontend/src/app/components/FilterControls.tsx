import { Search, Filter } from 'lucide-react';
import { FilterParams, MODALITY_OPTIONS, MANUFACTURER_OPTIONS } from '../utils/mockData';

interface FilterControlsProps {
  filters: FilterParams;
  onFiltersChange: (filters: FilterParams) => void;
  onSearch: () => void;
  isLoading: boolean;
}

export function FilterControls({ filters, onFiltersChange, onSearch, isLoading }: FilterControlsProps) {
  const updateFilter = (key: keyof FilterParams, value: any) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-blue-600" />
        <h2 className="font-semibold text-gray-900">Filter Controls</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Modality */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Modality
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.modality || ''}
            onChange={(e) => updateFilter('modality', e.target.value || undefined)}
          >
            <option value="">All</option>
            {MODALITY_OPTIONS.map(mod => (
              <option key={mod} value={mod}>{mod}</option>
            ))}
          </select>
        </div>

        {/* Manufacturer */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Manufacturer
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.manufacturer || ''}
            onChange={(e) => updateFilter('manufacturer', e.target.value || undefined)}
          >
            <option value="">All</option>
            {MANUFACTURER_OPTIONS.map(mfr => (
              <option key={mfr} value={mfr}>{mfr}</option>
            ))}
          </select>
        </div>

        {/* Study Date From */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Study Date From
          </label>
          <input
            type="date"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.studyDateFrom || ''}
            onChange={(e) => updateFilter('studyDateFrom', e.target.value || undefined)}
          />
        </div>

        {/* Study Date To */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Study Date To
          </label>
          <input
            type="date"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.studyDateTo || ''}
            onChange={(e) => updateFilter('studyDateTo', e.target.value || undefined)}
          />
        </div>

        {/* Series Description */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Series Description
          </label>
          <input
            type="text"
            placeholder="Search by series description..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={filters.seriesDescription || ''}
            onChange={(e) => updateFilter('seriesDescription', e.target.value || undefined)}
          />
        </div>

        {/* Slice Thickness Range */}
        <div className="md:col-span-2 lg:col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Slice Thickness (mm)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Min"
              step="0.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.sliceThicknessMin ?? ''}
              onChange={(e) => updateFilter('sliceThicknessMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
            <input
              type="number"
              placeholder="Max"
              step="0.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.sliceThicknessMax ?? ''}
              onChange={(e) => updateFilter('sliceThicknessMax', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Repetition Time Range */}
        <div className="md:col-span-2 lg:col-span-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Repetition Time (ms)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Min"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.repetitionTimeMin ?? ''}
              onChange={(e) => updateFilter('repetitionTimeMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
            <input
              type="number"
              placeholder="Max"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.repetitionTimeMax ?? ''}
              onChange={(e) => updateFilter('repetitionTimeMax', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Echo Time Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Echo Time (ms)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Min"
              step="0.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.echoTimeMin ?? ''}
              onChange={(e) => updateFilter('echoTimeMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
            <input
              type="number"
              placeholder="Max"
              step="0.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.echoTimeMax ?? ''}
              onChange={(e) => updateFilter('echoTimeMax', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Flip Angle Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Flip Angle (°)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Min"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.flipAngleMin ?? ''}
              onChange={(e) => updateFilter('flipAngleMin', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
            <input
              type="number"
              placeholder="Max"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filters.flipAngleMax ?? ''}
              onChange={(e) => updateFilter('flipAngleMax', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={onSearch}
          disabled={isLoading}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
        >
          <Search className="w-4 h-4" />
          {isLoading ? 'Searching...' : 'Apply Filters'}
        </button>
        <button
          onClick={() => onFiltersChange({})}
          className="px-6 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
        >
          Clear All
        </button>
      </div>
    </div>
  );
}
