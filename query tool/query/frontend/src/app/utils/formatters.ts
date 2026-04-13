export function formatDicomDate(value: unknown): string {
  const rawValue = String(value || '');
  if (!/^\d{8}$/.test(rawValue)) {
    return rawValue;
  }

  return `${rawValue.slice(6, 8)}-${rawValue.slice(4, 6)}-${rawValue.slice(0, 4)}`;
}

export function formatDisplayValue(header: string, value: unknown): string {
  if (value === undefined || value === null || value === '') {
    return '-';
  }

  if (header === 'StudyDate') {
    return formatDicomDate(value);
  }

  return String(value);
}
