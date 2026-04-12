import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { DicomInstance, getHeaderStats } from '../utils/dicomLoader';
import { TrendingUp, BarChart3 } from 'lucide-react';
import { useState } from 'react';

interface DynamicStatsPanelProps {
  instances: DicomInstance[];
  selectedInstances: DicomInstance[];
  allHeaders: string[];
}

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1', '#ef4444', '#06b6d4'];

export function DynamicStatsPanel({ instances, selectedInstances, allHeaders }: DynamicStatsPanelProps) {
  // Get first 4 headers from allHeaders dynamically as default stats
  const defaultStatsHeaders = allHeaders.slice(0, 4);
  
  const [selectedStatsHeaders, setSelectedStatsHeaders] = useState<string[]>(defaultStatsHeaders);

  const dataToAnalyze = selectedInstances.length > 0 ? selectedInstances : instances;

  const addStatsHeader = (header: string) => {
    if (!selectedStatsHeaders.includes(header)) {
      setSelectedStatsHeaders([...selectedStatsHeaders, header]);
    }
  };

  const removeStatsHeader = (header: string) => {
    setSelectedStatsHeaders(selectedStatsHeaders.filter(h => h !== header));
  };

  const renderChart = (header: string) => {
    const stats = getHeaderStats(dataToAnalyze, header);
    const entries = Object.entries(stats);

    // If too many unique values or empty, don't render
    if (entries.length === 0) {
      return (
        <div className="h-[250px] flex items-center justify-center text-gray-400">
          No data available
        </div>
      );
    }

    // Check if values are numeric
    const isNumeric = entries.every(([key]) => !isNaN(parseFloat(key)) && key.trim() !== '');

    if (entries.length <= 10 && !isNumeric) {
      // Categorical - use pie chart for few categories
      const data = entries.map(([name, value]) => ({
        name: name || '(empty)',
        value
      }));

      return (
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => 
                percent > 0.05 ? `${name.slice(0, 10)} ${(percent * 100).toFixed(0)}%` : ''
              }
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      );
    } else {
      // Many categories or numeric - use bar chart
      const sortedData = entries
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15) // Top 15
        .map(([name, count]) => ({
          name: name.slice(0, 20) || '(empty)',
          count
        }));

      return (
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={sortedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="name" 
              angle={-45} 
              textAnchor="end" 
              height={100}
              interval={0}
              tick={{ fontSize: 11 }}
            />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Results</p>
              <p className="text-2xl font-bold text-gray-900">{instances.length}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Selected</p>
              <p className="text-2xl font-bold text-blue-600">{selectedInstances.length}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Analyzing</p>
              <p className="text-2xl font-bold text-green-600">{dataToAnalyze.length}</p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {selectedInstances.length > 0 ? 'Selected subset' : 'All results'}
          </p>
        </div>
      </div>

      {/* Header Selector */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Statistics Visualization</h3>
          <select
            onChange={(e) => {
              if (e.target.value) {
                addStatsHeader(e.target.value);
                e.target.value = '';
              }
            }}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md"
            defaultValue=""
          >
            <option value="">+ Add Statistic</option>
            {allHeaders
              .filter(h => !selectedStatsHeaders.includes(h))
              .map(header => (
                <option key={header} value={header}>{header}</option>
              ))
            }
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          {selectedStatsHeaders.map(header => (
            <button
              key={header}
              onClick={() => removeStatsHeader(header)}
              className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-md hover:bg-blue-200"
            >
              {header}
              <span className="text-blue-500">×</span>
            </button>
          ))}
        </div>
      </div>

      {/* Stats Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {selectedStatsHeaders.map(header => (
          <div key={header} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">{header}</h3>
              <button
                onClick={() => removeStatsHeader(header)}
                className="text-gray-400 hover:text-red-500 text-sm"
              >
                Remove
              </button>
            </div>
            {renderChart(header)}
          </div>
        ))}
      </div>

      {selectedStatsHeaders.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="text-gray-400 mb-2">
            <BarChart3 className="w-12 h-12 mx-auto mb-3" />
          </div>
          <p className="text-gray-600">
            Select headers above to visualize their distribution
          </p>
        </div>
      )}
    </div>
  );
}