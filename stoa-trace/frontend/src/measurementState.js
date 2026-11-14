const units = new Set(['mm', 'cm', 'm', 'ft', 'in']);

export function validMeasurementPoints(points, minimum = 2, exact = false) {
  return Array.isArray(points) && points.length >= minimum && points.length <= 512
    && (!exact || points.length === minimum)
    && points.every(point => Array.isArray(point) && point.length === 2
      && point.every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1))
    && new Set(points.map(point => point.join(','))).size >= minimum;
}

export function parseMeasurementPoints(text) {
  if (typeof text !== 'string' || !text.trim()) return { points: [], error: '' };
  let points;
  try {
    if (text.trim().startsWith('[')) points = JSON.parse(text);
    else {
      const pairs = text.trim().split(/\n/).filter(line => line.trim()).map(line => line.trim().split(/[,\s]+/));
      if (pairs.some(pair => pair.length !== 2 || pair.some(value => !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value)))) {
        throw new Error('Invalid coordinate pair');
      }
      points = pairs.map(pair => pair.map(Number));
    }
  } catch {
    return { points: [], error: 'Enter one x, y pair per line, with both coordinates between 0 and 1.' };
  }
  if (!validMeasurementPoints(points, 1)) {
    return { points: [], error: 'Enter one x, y pair per line, with both coordinates between 0 and 1.' };
  }
  return { points, error: '' };
}

export function measurementDraft({ documentId, page, context, reference, geometry, value, unit, kind }) {
  if (!documentId || !Number.isInteger(page) || page < 1 || !context?.source_fingerprint || context.page !== page) {
    return { error: 'The drawing must finish loading before measuring.' };
  }
  if (!units.has(unit) || typeof value === 'boolean' || String(value).trim() === ''
      || !Number.isFinite(Number(value)) || Number(value) <= 0) {
    return { error: 'Enter a positive reference length and its unit.' };
  }
  if (!validMeasurementPoints(reference, 2, true)) return { error: 'Mark two distinct endpoints for the known reference length.' };
  if (!['area', 'length'].includes(kind)) return { error: 'Choose area or length.' };
  if (!validMeasurementPoints(geometry, kind === 'area' ? 3 : 2, kind === 'length')) {
    return { error: kind === 'area' ? 'Mark at least three distinct outline vertices.' : 'Mark two distinct endpoints for the measured length.' };
  }
  return { error: '', payload: {
    page, kind, source_fingerprint: context.source_fingerprint,
    calibration: { page, document_id: documentId, points: reference.map(point => [...point]), value: Number(value), unit },
    geometry: geometry.map(point => [...point]),
  } };
}
