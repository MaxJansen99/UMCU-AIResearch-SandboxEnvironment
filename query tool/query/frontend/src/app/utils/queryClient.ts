import type { DicomInstance, DicomStats, DynamicFilters } from './dicomLoader';

export const CORE_METADATA_TAGS = [
  'Modality',
  'PatientBirthDate',
  'BodyPartExamined',
  'PatientSex',
] as const;

type QueryResponse = {
  ok: boolean;
  error?: string;
  stats?: Record<string, Record<string, number>>;
  matched_series?: Array<Record<string, unknown>>;
  match_count?: number;
  total_series_found?: number;
  total_instances_in_pacs?: number;
  elapsed_seconds?: number;
};

type QueryResult = {
  stats: DicomStats;
  instances: DicomInstance[];
};

export async function loadOrthancMetadata(): Promise<QueryResult> {
  return queryOrthancMetadata({});
}

export async function queryOrthancMetadata(filters: DynamicFilters): Promise<QueryResult> {
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filters: toBackendFilters(filters),
      stats_tags: CORE_METADATA_TAGS,
    }),
  });

  if (!response.ok) {
    throw new Error(`Query failed with HTTP ${response.status}`);
  }

  const payload = (await response.json()) as QueryResponse;
  if (!payload.ok) {
    throw new Error(payload.error || 'Orthanc query failed.');
  }

  const instances = (payload.matched_series || []).map(toDicomInstance);
  const stats = ensureCoreStats(payload.stats || {}, instances);

  return {
    stats: {
      stats,
      total_series: payload.match_count ?? payload.total_series_found ?? instances.length,
      total_instances: sumInstances(instances) || payload.total_instances_in_pacs,
      elapsed_seconds: payload.elapsed_seconds,
      instances,
    },
    instances,
  };
}

function toBackendFilters(filters: DynamicFilters): Array<[string, string, unknown]> {
  const backendFilters: Array<[string, string, unknown]> = [];

  for (const [header, config] of Object.entries(filters)) {
    if (config.type === 'ageGroup' && Array.isArray(config.value) && config.value.length > 0) {
      backendFilters.push([header, 'date in ranges', ageGroupsToBirthDateRanges(config.value)]);
    } else if (Array.isArray(config.value) && config.value.length > 0) {
      backendFilters.push([header, 'in', config.value]);
    } else if (config.value !== undefined && config.value !== '') {
      if (config.type === 'text') {
        backendFilters.push([header, 'contains', config.value]);
      } else {
        backendFilters.push([header, '==', config.value]);
      }
    }

    if (config.min !== undefined) {
      backendFilters.push([header, '>=', config.min]);
    }
    if (config.max !== undefined) {
      backendFilters.push([header, '<=', config.max]);
    }
  }

  return backendFilters;
}

function ageGroupsToBirthDateRanges(ageGroups: string[]): Array<{ min?: string; max?: string }> {
  return ageGroups.map(ageGroupToBirthDateRange).filter(Boolean) as Array<{ min?: string; max?: string }>;
}

function ageGroupToBirthDateRange(ageGroup: string): { min?: string; max?: string } | undefined {
  const today = new Date();

  if (ageGroup === '0-18') {
    return { min: toDicomDate(addYears(today, -18)) };
  }
  if (ageGroup === '18-40') {
    return { min: toDicomDate(addYears(today, -40)), max: toDicomDate(addYears(today, -18)) };
  }
  if (ageGroup === '40-65') {
    return { min: toDicomDate(addYears(today, -65)), max: toDicomDate(addYears(today, -40)) };
  }
  if (ageGroup === '65+') {
    return { max: toDicomDate(addYears(today, -65)) };
  }

  return undefined;
}

function addYears(date: Date, years: number): Date {
  const nextDate = new Date(date);
  nextDate.setFullYear(nextDate.getFullYear() + years);
  return nextDate;
}

function toDicomDate(date: Date): string {
  const year = String(date.getFullYear()).padStart(4, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

function toDicomInstance(series: Record<string, unknown>): DicomInstance {
  return {
    id: String(series.id || series.series_instance_uid || randomId()),
    OrthancStudyID: stringValue(series.orthanc_study_id),
    Modality: stringValue(series.modality),
    PatientID: stringValue(series.patient_id),
    PatientBirthDate: stringValue(series.patient_birth_date),
    BodyPartExamined: stringValue(series.body_part_examined),
    PatientSex: stringValue(series.patient_sex),
    StudyDate: stringValue(series.study_date),
    StudyDescription: stringValue(series.study_description),
    SeriesDescription: stringValue(series.series_description),
    Images: numberValue(series.instances),
    StudyInstanceUID: stringValue(series.study_instance_uid),
    SeriesInstanceUID: stringValue(series.series_instance_uid),
  };
}

function ensureCoreStats(
  stats: Record<string, Record<string, number>>,
  instances: DicomInstance[]
): Record<string, Record<string, number>> {
  const orderedStats: Record<string, Record<string, number>> = {};

  for (const tag of CORE_METADATA_TAGS) {
    orderedStats[tag] = stats[tag] || countValues(instances, tag);
  }

  return orderedStats;
}

function countValues(instances: DicomInstance[], key: string): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const instance of instances) {
    const value = String(instance[key] || 'onbekend');
    counts[value] = (counts[value] || 0) + 1;
  }
  return counts;
}

function sumInstances(instances: DicomInstance[]): number {
  return instances.reduce((total, instance) => total + numberValue(instance.Images), 0);
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function numberValue(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function randomId(): string {
  if ('crypto' in globalThis && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `series-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
