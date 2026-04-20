import { CheckSquare, Square, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { DicomInstance } from '../utils/dicomLoader';
import { formatDisplayValue, formatHeaderLabel } from '../utils/formatters';
import { useEffect, useState } from 'react';

interface DynamicTableProps {
  instances: DicomInstance[];
  allHeaders: string[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  getSelectionId?: (instance: DicomInstance) => string;
}

export function DynamicTable({
  instances,
  allHeaders,
  selectedIds,
  onSelectionChange,
  currentPage,
  pageSize,
  onPageChange,
  getSelectionId = (instance) => instance.id
}: DynamicTableProps) {
  // Get first 6 headers from stats dynamically as default visible columns
  const defaultVisibleHeaders = allHeaders.slice(0, 6);
  
  const [visibleHeaders, setVisibleHeaders] = useState<string[]>(defaultVisibleHeaders);
  const [showColumnSelector, setShowColumnSelector] = useState(false);

  useEffect(() => {
    setVisibleHeaders(defaultVisibleHeaders);
  }, [allHeaders.join('|')]);

  const startIndex = currentPage * pageSize;
  const endIndex = Math.min(startIndex + pageSize, instances.length);
  const visibleInstances = instances.slice(startIndex, endIndex);
  const totalPages = Math.ceil(instances.length / pageSize);

  const toggleSelectAll = () => {
    const allIds = instances.map(getSelectionId);
    const allSelected = allIds.length > 0 && allIds.every(id => selectedIds.has(id));

    const newSelection = new Set(selectedIds);
    if (allSelected) {
      allIds.forEach(id => newSelection.delete(id));
    } else {
      allIds.forEach(id => newSelection.add(id));
    }
    onSelectionChange(newSelection);
  };

  const toggleSelectOne = (id: string) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    onSelectionChange(newSelection);
  };

  const allSelected = instances.length > 0 && instances.every(i => selectedIds.has(getSelectionId(i)));

  const toggleHeaderVisibility = (header: string) => {
    if (visibleHeaders.includes(header)) {
      setVisibleHeaders(visibleHeaders.filter(h => h !== header));
    } else {
      setVisibleHeaders([...visibleHeaders, header]);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-semibold text-gray-900">Results: </span>
            <span className="text-gray-600">
              {instances.length} total, {selectedIds.size} selected
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowColumnSelector(!showColumnSelector)}
              className="flex items-center gap-1 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              <Eye className="w-4 h-4" />
              Columns ({visibleHeaders.length})
            </button>
            <div className="text-sm text-gray-600">
              Showing {startIndex + 1}-{endIndex} of {instances.length}
            </div>
          </div>
        </div>

        {showColumnSelector && (
          <div className="mt-3 p-3 bg-gray-50 rounded-md">
            <div className="text-xs font-medium text-gray-700 mb-2">Select columns to display:</div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-60 overflow-y-auto">
              {allHeaders.map(header => (
                <label key={header} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-100 p-1 rounded">
                  <input
                    type="checkbox"
                    checked={visibleHeaders.includes(header)}
                    onChange={() => toggleHeaderVisibility(header)}
                    className="rounded"
                  />
                  <span className="truncate" title={header}>{formatHeaderLabel(header)}</span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left sticky left-0 bg-gray-50 z-10">
                <button
                  onClick={toggleSelectAll}
                  className="flex items-center gap-2 hover:text-blue-600 transition-colors"
                  title={allSelected ? "Deselect all results" : "Select all results"}
                >
                  {allSelected ? (
                    <CheckSquare className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Square className="w-5 h-5" />
                  )}
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-700">All</span>
                </button>
              </th>
              {visibleHeaders.map(header => (
                <th
                  key={header}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider whitespace-nowrap"
                >
                  {formatHeaderLabel(header)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {visibleInstances.length === 0 ? (
              <tr>
                <td colSpan={visibleHeaders.length + 1} className="px-4 py-8 text-center text-gray-500">
                  No results found. Try adjusting your filters.
                </td>
              </tr>
            ) : (
              visibleInstances.map((instance) => (
                <tr
                  key={instance.id}
                  className={`hover:bg-gray-50 transition-colors ${
                    selectedIds.has(getSelectionId(instance)) ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3 sticky left-0 bg-inherit z-10">
                    <button
                      onClick={() => toggleSelectOne(getSelectionId(instance))}
                      className="flex items-center hover:text-blue-600 transition-colors"
                    >
                      {selectedIds.has(getSelectionId(instance)) ? (
                        <CheckSquare className="w-5 h-5 text-blue-600" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>
                  </td>
                  {visibleHeaders.map(header => {
                    const value = instance[header];
                    const displayValue = formatDisplayValue(header, value);
                    const isLongValue = displayValue.length > 50;
                    
                    return (
                      <td
                        key={header}
                        className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate"
                        title={isLongValue ? displayValue : undefined}
                      >
                        {isLongValue ? `${displayValue.slice(0, 50)}...` : displayValue}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {instances.length > pageSize && (
        <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 0}
            className="flex items-center gap-1 px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>

          <div className="flex items-center gap-2">
            <div className="text-sm text-gray-600">
              Page {currentPage + 1} of {totalPages}
            </div>
            {totalPages > 1 && (
              <select
                value={currentPage}
                onChange={(e) => onPageChange(parseInt(e.target.value))}
                className="px-2 py-1 text-sm border border-gray-300 rounded-md"
              >
                {Array.from({ length: totalPages }, (_, i) => (
                  <option key={i} value={i}>
                    {i + 1}
                  </option>
                ))}
              </select>
            )}
          </div>

          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages - 1}
            className="flex items-center gap-1 px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
