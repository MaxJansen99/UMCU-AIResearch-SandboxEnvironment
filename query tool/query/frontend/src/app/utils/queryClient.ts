import type { DicomInstance, DicomStats, DynamicFilters } from './dicomLoader';

export const CORE_METADATA_TAGS = [
  'Modality',
  'StudyDate',
  'StudyDescription',
  'SeriesDescription',
  'BodyPartExamined',
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
  const response = await fetch('/query', {
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
    if (config.value !== undefined && config.value !== '') {
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

function toDicomInstance(series: Record<string, unknown>): DicomInstance {
  return {
    id: String(series.id || series.series_instance_uid || randomId()),
    Modality: stringValue(series.modality),
    StudyDate: stringValue(series.study_date),
    StudyDescription: stringValue(series.study_description),
    SeriesDescription: stringValue(series.series_description),
    BodyPartExamined: stringValue(series.body_part_examined),
    Instances: numberValue(series.instances),
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
  return instances.reduce((total, instance) => total + numberValue(instance.Instances), 0);
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
