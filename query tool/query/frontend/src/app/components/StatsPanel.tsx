import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { DicomInstance } from '../utils/mockData';
import { TrendingUp } from 'lucide-react';

interface StatsPanelProps {
  instances: DicomInstance[];
  selectedInstances: DicomInstance[];
}

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'];

export function StatsPanel({ instances, selectedInstances }: StatsPanelProps) {
  const dataToAnalyze = selectedInstances.length > 0 ? selectedInstances : instances;

  // Categorical stats: Modality
  const modalityStats = dataToAnalyze.reduce((acc, inst) => {
    acc[inst.modality] = (acc[inst.modality] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const modalityData = Object.entries(modalityStats).map(([name, value]) => ({
    name,
    value
  }));

  // Categorical stats: Manufacturer
  const manufacturerStats = dataToAnalyze.reduce((acc, inst) => {
    acc[inst.manufacturer] = (acc[inst.manufacturer] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const manufacturerData = Object.entries(manufacturerStats).map(([name, value]) => ({
    name,
    value
  }));

  // Numeric stats: Slice Thickness histogram
  const sliceThicknessData = dataToAnalyze
    .filter(i => i.sliceThickness !== null)
    .map(i => i.sliceThickness!);

  const sliceThicknessHistogram = createHistogram(sliceThicknessData, 10);

  // Numeric stats: Repetition Time histogram
  const repetitionTimeData = dataToAnalyze
    .filter(i => i.repetitionTime !== null)
    .map(i => i.repetitionTime!);

  const repetitionTimeHistogram = createHistogram(repetitionTimeData, 10);

  // Numeric stats: Echo Time histogram
  const echoTimeData = dataToAnalyze
    .filter(i => i.echoTime !== null)
    .map(i => i.echoTime!);

  const echoTimeHistogram = createHistogram(echoTimeData, 10);

  // Numeric stats: Flip Angle histogram
  const flipAngleData = dataToAnalyze
    .filter(i => i.flipAngle !== null)
    .map(i => i.flipAngle!);

  const flipAngleHistogram = createHistogram(flipAngleData, 10);

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
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {selectedInstances.length > 0 ? 'Selected subset' : 'All results'}
          </p>
        </div>
      </div>

      {/* Categorical Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Modality Distribution */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Modality Distribution</h3>
          {modalityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={modalityData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {modalityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>

        {/* Manufacturer Distribution */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Manufacturer Distribution</h3>
          {manufacturerData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={manufacturerData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Numeric Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Slice Thickness */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Slice Thickness Distribution (mm)</h3>
          {sliceThicknessHistogram.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sliceThicknessHistogram}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>

        {/* Repetition Time */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Repetition Time Distribution (ms)</h3>
          {repetitionTimeHistogram.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={repetitionTimeHistogram}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#ec4899" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>

        {/* Echo Time */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Echo Time Distribution (ms)</h3>
          {echoTimeHistogram.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={echoTimeHistogram}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>

        {/* Flip Angle */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Flip Angle Distribution (°)</h3>
          {flipAngleHistogram.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={flipAngleHistogram}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-gray-400">
              No data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper function to create histogram bins
function createHistogram(data: number[], bins: number): Array<{ range: string; count: number }> {
  if (data.length === 0) return [];

  const min = Math.min(...data);
  const max = Math.max(...data);
  const binSize = (max - min) / bins;

  const histogram = Array.from({ length: bins }, (_, i) => {
    const start = min + i * binSize;
    const end = start + binSize;
    const count = data.filter(v => v >= start && (i === bins - 1 ? v <= end : v < end)).length;
    return {
      range: `${start.toFixed(1)}-${end.toFixed(1)}`,
      count
    };
  });

  return histogram.filter(h => h.count > 0);
}
