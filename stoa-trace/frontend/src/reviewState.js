// Pure review and display helpers. Source values remain immutable in the API.
export function evidenceBox(evidence) {
  const box = evidence?.bbox;
  if (Array.isArray(box) && box.length === 4 && box.every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1)) {
    const normalized = box.map(Number);
    if (normalized[0] < normalized[2] && normalized[1] < normalized[3]) return normalized;
  }
  const points = evidence?.polygon;
  if (!Array.isArray(points) || points.length < 3 || !points.every(point => Array.isArray(point) && point.length >= 2 && point.slice(0, 2).every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1))) return null;
  const xs = points.map(point => Number(point[0]));
  const ys = points.map(point => Number(point[1]));
  const result = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  return result[0] < result[2] && result[1] < result[3] ? result : null;
}

export function evidenceKind(item) {
  if (item?.manual || item?.source === 'manual' || item?.method === 'manual' || item?.origin === 'human' || String(item?.id || '').startsWith('manual-')) return 'manual';
  if (item?.source_verified === false || item?.method === 'vision' || item?.origin === 'visual' || String(item?.id || '').startsWith('vision-') || String(item?.id || '').startsWith('inventory-')) return 'visual';
  return 'native';
}

export function savedAdditions(answer) {
  const direct = answer?.added_evidence || answer?.review?.added_evidence;
  return Array.isArray(direct) ? direct : (answer?.evidence || []).filter(item => evidenceKind(item) === 'manual');
}

export function originalEvidence(answer) {
  return Array.isArray(answer?.original_evidence) ? answer.original_evidence : (answer?.evidence || []).filter(item => evidenceKind(item) !== 'manual');
}

export function reviewEvidence(answer, additions = []) {
  const byId = new Map();
  [...originalEvidence(answer), ...additions].forEach((item, index) => byId.set(String(item.id ?? `evidence-${index}`), item));
  return [...byId.values()];
}

export function reviewCount(answer, additions, excluded) {
  return reviewEvidence(answer, additions).filter((item, index) => !excluded.includes(String(item.id ?? `evidence-${index}`))).length;
}

export function reviewFingerprint(excluded, additions, note = '') {
  return JSON.stringify({ excluded: [...excluded].sort(), additions, note });
}

export function costText(usage) {
  if (!usage) return 'Usage unavailable';
  if (Number.isFinite(usage.cost_estimate_usd)) return usage.cost_estimate_usd === 0 ? '$0 estimated' : `$${usage.cost_estimate_usd.toFixed(4)} estimated`;
  if (usage.cost_basis === 'native' && Number(usage.model_calls || 0) === 0) return '$0 model inference';
  return 'Cost unavailable';
}

export function aggregateUsage(value) {
  if (!Array.isArray(value)) return value || null;
  if (!value.length) return null;
  const fields = ['model_calls', 'input_tokens', 'output_tokens', 'cached_input_tokens'];
  const total = Object.fromEntries(fields.map(field => [field, value.reduce((sum, item) => sum + Number(item[field] || 0), 0)]));
  total.cost_estimate_usd = value.every(item => Number.isFinite(item.cost_estimate_usd)) ? value.reduce((sum, item) => sum + item.cost_estimate_usd, 0) : null;
  total.cost_basis = value.every(item => item.cost_basis === 'native') ? 'native' : total.cost_estimate_usd == null ? 'unconfigured' : 'configured_rates';
  return total;
}
