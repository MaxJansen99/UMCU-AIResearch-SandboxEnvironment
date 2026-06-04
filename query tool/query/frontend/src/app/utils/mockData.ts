// Mock DICOM metadata types and data generator

export interface DicomInstance {
  id: string;
  instanceUID: string;
  modality: string;
  manufacturer: string;
  studyDate: string;
  seriesDescription: string;
  sliceThickness: number | null;
  repetitionTime: number | null;
  echoTime: number | null;
  flipAngle: number | null;
}

export interface FilterParams {
  modality?: string;
  manufacturer?: string;
  studyDateFrom?: string;
  studyDateTo?: string;
  seriesDescription?: string;
  sliceThicknessMin?: number;
  sliceThicknessMax?: number;
  repetitionTimeMin?: number;
  repetitionTimeMax?: number;
  echoTimeMin?: number;
  echoTimeMax?: number;
  flipAngleMin?: number;
  flipAngleMax?: number;
}

const modalities = ['CT', 'MRI', 'XR', 'US', 'PT', 'NM'];
const manufacturers = ['Siemens', 'GE Healthcare', 'Philips', 'Canon', 'Hitachi'];
const seriesDescriptions = [
  'T1 MPRAGE',
  'T2 FLAIR',
  'DWI',
  'Chest CT',
  'Abdomen CT',
  'Brain MRI',
  'Cardiac MRI',
  'Pelvis CT',
  'Spine MRI',
  'Angio CT'
];

// Generate mock DICOM instances
export function generateMockInstances(count: number = 100): DicomInstance[] {
  const instances: DicomInstance[] = [];
  const baseDate = new Date('2024-01-01');

  for (let i = 0; i < count; i++) {
    const modality = modalities[Math.floor(Math.random() * modalities.length)];
    const isMRI = modality === 'MRI';
    
    // Generate dates spanning several months
    const dayOffset = Math.floor(Math.random() * 365);
    const studyDate = new Date(baseDate.getTime() + dayOffset * 24 * 60 * 60 * 1000);

    instances.push({
      id: `instance-${i + 1}`,
      instanceUID: `1.2.840.113619.2.${Math.floor(Math.random() * 1000000)}.${i}`,
      modality,
      manufacturer: manufacturers[Math.floor(Math.random() * manufacturers.length)],
      studyDate: studyDate.toISOString().split('T')[0],
      seriesDescription: seriesDescriptions[Math.floor(Math.random() * seriesDescriptions.length)],
      sliceThickness: modality === 'CT' || isMRI ? parseFloat((Math.random() * 5 + 0.5).toFixed(2)) : null,
      repetitionTime: isMRI ? parseFloat((Math.random() * 2000 + 500).toFixed(1)) : null,
      echoTime: isMRI ? parseFloat((Math.random() * 100 + 10).toFixed(1)) : null,
      flipAngle: isMRI ? Math.floor(Math.random() * 180 + 10) : null,
    });
  }

  return instances;
}

// Mock API query function
export async function queryInstances(filters: FilterParams): Promise<DicomInstance[]> {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 500));

  let instances = generateMockInstances(150);

  // Apply filters
  if (filters.modality) {
    instances = instances.filter(i => i.modality === filters.modality);
  }

  if (filters.manufacturer) {
    instances = instances.filter(i => i.manufacturer === filters.manufacturer);
  }

  if (filters.studyDateFrom) {
    instances = instances.filter(i => i.studyDate >= filters.studyDateFrom!);
  }

  if (filters.studyDateTo) {
    instances = instances.filter(i => i.studyDate <= filters.studyDateTo!);
  }

  if (filters.seriesDescription) {
    instances = instances.filter(i =>
      i.seriesDescription.toLowerCase().includes(filters.seriesDescription!.toLowerCase())
    );
  }

  if (filters.sliceThicknessMin !== undefined) {
    instances = instances.filter(i => 
      i.sliceThickness !== null && i.sliceThickness >= filters.sliceThicknessMin!
    );
  }

  if (filters.sliceThicknessMax !== undefined) {
    instances = instances.filter(i => 
      i.sliceThickness !== null && i.sliceThickness <= filters.sliceThicknessMax!
    );
  }

  if (filters.repetitionTimeMin !== undefined) {
    instances = instances.filter(i => 
      i.repetitionTime !== null && i.repetitionTime >= filters.repetitionTimeMin!
    );
  }

  if (filters.repetitionTimeMax !== undefined) {
    instances = instances.filter(i => 
      i.repetitionTime !== null && i.repetitionTime <= filters.repetitionTimeMax!
    );
  }

  if (filters.echoTimeMin !== undefined) {
    instances = instances.filter(i => 
      i.echoTime !== null && i.echoTime >= filters.echoTimeMin!
    );
  }

  if (filters.echoTimeMax !== undefined) {
    instances = instances.filter(i => 
      i.echoTime !== null && i.echoTime <= filters.echoTimeMax!
    );
  }

  if (filters.flipAngleMin !== undefined) {
    instances = instances.filter(i => 
      i.flipAngle !== null && i.flipAngle >= filters.flipAngleMin!
    );
  }

  if (filters.flipAngleMax !== undefined) {
    instances = instances.filter(i => 
      i.flipAngle !== null && i.flipAngle <= filters.flipAngleMax!
    );
  }

  return instances;
}

export const MODALITY_OPTIONS = modalities;
export const MANUFACTURER_OPTIONS = manufacturers;
