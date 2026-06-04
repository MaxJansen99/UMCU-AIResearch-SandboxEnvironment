import { CheckSquare, Square, ChevronLeft, ChevronRight } from 'lucide-react';
import { DicomInstance } from '../utils/mockData';

interface ResultsTableProps {
  instances: DicomInstance[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function ResultsTable({
  instances,
  selectedIds,
  onSelectionChange,
  currentPage,
  pageSize,
  onPageChange
}: ResultsTableProps) {
  const startIndex = currentPage * pageSize;
  const endIndex = Math.min(startIndex + pageSize, instances.length);
  const visibleInstances = instances.slice(startIndex, endIndex);
  const totalPages = Math.ceil(instances.length / pageSize);

  const toggleSelectAll = () => {
    const visibleIds = visibleInstances.map(i => i.id);
    const allSelected = visibleIds.every(id => selectedIds.has(id));

    const newSelection = new Set(selectedIds);
    if (allSelected) {
      visibleIds.forEach(id => newSelection.delete(id));
    } else {
      visibleIds.forEach(id => newSelection.add(id));
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

  const allVisibleSelected = visibleInstances.length > 0 && 
    visibleInstances.every(i => selectedIds.has(i.id));

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
          <div className="text-sm text-gray-600">
            Showing {startIndex + 1}-{endIndex} of {instances.length}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left">
                <button
                  onClick={toggleSelectAll}
                  className="flex items-center hover:text-blue-600 transition-colors"
                  title={allVisibleSelected ? "Deselect all visible" : "Select all visible"}
                >
                  {allVisibleSelected ? (
                    <CheckSquare className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Square className="w-5 h-5" />
                  )}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Instance UID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Modality
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Manufacturer
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Study Date
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                Series Description
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                Slice (mm)
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                TR (ms)
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                TE (ms)
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                Flip (°)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {visibleInstances.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                  No results found. Try adjusting your filters.
                </td>
              </tr>
            ) : (
              visibleInstances.map((instance) => (
                <tr
                  key={instance.id}
                  className={`hover:bg-gray-50 transition-colors ${
                    selectedIds.has(instance.id) ? 'bg-blue-50' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleSelectOne(instance.id)}
                      className="flex items-center hover:text-blue-600 transition-colors"
                    >
                      {selectedIds.has(instance.id) ? (
                        <CheckSquare className="w-5 h-5 text-blue-600" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 font-mono">
                    {instance.instanceUID.slice(0, 24)}...
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {instance.modality}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {instance.manufacturer}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {instance.studyDate}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {instance.seriesDescription}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">
                    {instance.sliceThickness?.toFixed(2) ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">
                    {instance.repetitionTime?.toFixed(1) ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">
                    {instance.echoTime?.toFixed(1) ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">
                    {instance.flipAngle ?? '—'}
                  </td>
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

          <div className="text-sm text-gray-600">
            Page {currentPage + 1} of {totalPages}
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
