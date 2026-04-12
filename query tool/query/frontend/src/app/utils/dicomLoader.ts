import { loadOrthancMetadata } from './queryClient';

export interface DicomStats {
  stats: Record<string, Record<string, number>>;
  total_series?: number;
  total_instances?: number;
  elapsed_seconds?: number;
  timestamp?: number;
  instances?: DicomInstance[];
}

export interface DicomInstance {
  id: string;
  [key: string]: any; // Dynamic fields based on stats.json
}

export interface FilterConfig {
  headerName: string;
  values: string[];
  type: 'categorical' | 'numeric' | 'text';
}

// Load stats from the backend, which proxies Orthanc metadata.
export async function loadDicomStats(): Promise<DicomStats> {
  try {
    return (await loadOrthancMetadata()).stats;
  } catch (error) {
    console.error('Error in loadDicomStats:', error);
    throw error;
  }
}

// Analyze stats to determine filter types dynamically
export function analyzeHeader(headerName: string, values: Record<string, number>): FilterConfig {
  const uniqueValues = Object.keys(values);
  
  // Check if all values are numeric
  const allNumeric = uniqueValues.every(v => {
    const num = parseFloat(v);
    return !isNaN(num) && v.trim() !== '';
  });

  // If numeric and has many unique values, treat as numeric range
  if (allNumeric && uniqueValues.length > 10) {
    return {
      headerName,
      values: uniqueValues,
      type: 'numeric'
    };
  }

  // If categorical with reasonable number of options (< 20), use dropdown
  if (uniqueValues.length <= 20 && uniqueValues.length > 0) {
    return {
      headerName,
      values: uniqueValues,
      type: 'categorical'
    };
  }

  // Otherwise, text search
  return {
    headerName,
    values: uniqueValues,
    type: 'text'
  };
}

// Generate individual instances from aggregate stats
export function generateInstancesFromStats(stats: DicomStats, count?: number): DicomInstance[] {
  if (stats.instances) {
    return stats.instances;
  }

  const { stats: headerStats, total_instances } = stats;
  
  // Use total_instances from the stats file if available, otherwise use the provided count or default
  const instanceCount = total_instances || count || 2315;
  
  const instances: DicomInstance[] = [];
  
  // Get all headers dynamically from the stats
  const headers = Object.keys(headerStats);
  
  // Create value pools for each header based on their distribution
  const valuePools: Record<string, string[]> = {};
  
  for (const header of headers) {
    const distribution = headerStats[header];
    const pool: string[] = [];
    
    // Create weighted pool based on counts
    for (const [value, count] of Object.entries(distribution)) {
      for (let i = 0; i < count; i++) {
        pool.push(value);
      }
    }
    
    valuePools[header] = pool;
  }
  
  // Generate instances by sampling from pools
  for (let i = 0; i < instanceCount; i++) {
    const instance: DicomInstance = {
      id: `instance-${i + 1}`,
    };
    
    for (const header of headers) {
      const pool = valuePools[header];
      if (pool && pool.length > 0) {
        // Sample from the pool
        const randomIndex = Math.floor(Math.random() * pool.length);
        instance[header] = pool[randomIndex];
      } else {
        instance[header] = '';
      }
    }
    
    instances.push(instance);
  }
  
  return instances;
}

// Get all available headers from stats
export function getAvailableHeaders(stats: DicomStats): string[] {
  return Object.keys(stats.stats);
}

// Filter instances based on dynamic criteria
export interface DynamicFilters {
  [headerName: string]: {
    type: 'categorical' | 'numeric' | 'text';
    value?: string | string[];
    min?: number;
    max?: number;
  };
}

export function filterInstances(instances: DicomInstance[], filters: DynamicFilters): DicomInstance[] {
  return instances.filter(instance => {
    for (const [headerName, filterConfig] of Object.entries(filters)) {
      const instanceValue = instance[headerName];
      
      if (!filterConfig.value && filterConfig.min === undefined && filterConfig.max === undefined) {
        continue; // No filter set for this header
      }
      
      switch (filterConfig.type) {
        case 'categorical':
          if (Array.isArray(filterConfig.value)) {
            if (!filterConfig.value.includes(instanceValue)) {
              return false;
            }
          } else if (filterConfig.value && instanceValue !== filterConfig.value) {
            return false;
          }
          break;
          
        case 'text':
          if (filterConfig.value && typeof filterConfig.value === 'string') {
            const searchText = filterConfig.value.toLowerCase();
            const fieldValue = String(instanceValue || '').toLowerCase();
            if (!fieldValue.includes(searchText)) {
              return false;
            }
          }
          break;
          
        case 'numeric':
          const numValue = parseFloat(instanceValue);
          if (isNaN(numValue)) {
            return false;
          }
          if (filterConfig.min !== undefined && numValue < filterConfig.min) {
            return false;
          }
          if (filterConfig.max !== undefined && numValue > filterConfig.max) {
            return false;
          }
          break;
      }
    }
    
    return true;
  });
}

// Get statistics for a specific header from instances
export function getHeaderStats(instances: DicomInstance[], headerName: string): Record<string, number> {
  const stats: Record<string, number> = {};
  
  for (const instance of instances) {
    const value = String(instance[headerName] || '');
    stats[value] = (stats[value] || 0) + 1;
  }
  
  return stats;
}
