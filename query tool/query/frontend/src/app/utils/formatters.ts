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

  if (header === 'PatientBirthDate' || header === 'StudyDate') {
    return formatDicomDate(value);
  }

  return String(value);
}

export function formatHeaderLabel(header: string): string {
  const labels: Record<string, string> = {
    BodyPartExamined: 'Anatomical region',
    Images: 'Images',
    Modality: 'Modality',
    PatientBirthDate: 'Age',
    PatientID: 'Patient ID',
    PatientSex: 'Sex',
    SeriesDescription: 'Series description',
    StudyInstanceUID: 'Study ID',
    StudyDate: 'Study date',
    StudyDescription: 'Study description',
  };

  return labels[header] || header;
}
