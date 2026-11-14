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

export function evidenceBoxCenter(evidence) {
  const box = evidenceBox(evidence);
  if (!box) return null;
  return [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2];
}

export function evidenceKind(item) {
  if (item?.evidence_kind === 'manual' || item?.manual || item?.source === 'manual' || item?.method === 'manual' || item?.origin === 'human' || String(item?.id || '').startsWith('manual-')) return 'manual';
  if (item?.evidence_kind === 'native' || item?.evidence_kind === 'visual') return item.evidence_kind;
  if (item?.method === 'vision' || item?.origin === 'visual' || /^(?:vision|visual|inventory)-/.test(String(item?.id || ''))) return 'visual';
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

export function createSessionTracker() {
  return {
    queriesCount: 0,
    modelCalls: 0,
    inputTokens: 0,
    outputTokens: 0,
    cachedTokens: 0,
    totalCostUsd: 0,
    hasCostEstimate: false,
  };
}

export function recordSessionQuery(tracker, usage) {
  const current = tracker || createSessionTracker();
  if (!usage) {
    return {
      ...current,
      queriesCount: current.queriesCount + 1,
    };
  }
  const inputTokens = Number(usage.input_tokens || 0);
  const outputTokens = Number(usage.output_tokens || 0);
  const cachedTokens = Number(usage.cached_input_tokens || 0);
  const modelCalls = Number(usage.model_calls || 0);
  const cost = Number.isFinite(usage.cost_estimate_usd) ? usage.cost_estimate_usd : 0;
  const hasCost = Number.isFinite(usage.cost_estimate_usd);

  return {
    queriesCount: current.queriesCount + 1,
    modelCalls: current.modelCalls + modelCalls,
    inputTokens: current.inputTokens + inputTokens,
    outputTokens: current.outputTokens + outputTokens,
    cachedTokens: current.cachedTokens + cachedTokens,
    totalCostUsd: current.totalCostUsd + cost,
    hasCostEstimate: current.hasCostEstimate || hasCost,
  };
}

export function formatCostDetail(usage) {
  if (!usage) return { costStr: '$0.0000', detailStr: 'No model calls', tokensTotal: 0 };
  const tokensTotal = Number(usage.input_tokens || 0) + Number(usage.output_tokens || 0);
  const costStr = Number.isFinite(usage.cost_estimate_usd)
    ? `$${usage.cost_estimate_usd.toFixed(4)}`
    : usage.cost_basis === 'native' || Number(usage.model_calls || 0) === 0
      ? '$0.0000 (Free)'
      : 'Unrated';
  const detailStr = tokensTotal > 0
    ? `${tokensTotal.toLocaleString()} tokens (${Number(usage.input_tokens || 0)} in / ${Number(usage.output_tokens || 0)} out)`
    : usage.model_calls > 0
      ? `${usage.model_calls} model call(s)`
      : 'Deterministic CAD (zero tokens)';
  return { costStr, detailStr, tokensTotal };
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


export const reviewCategories = ['door', 'window', 'apartment', 'toilet', 'sink', 'bathtub', 'shower', 'bedroom', 'kitchen', 'balcony', 'sauna', 'bathroom', 'wc_room', 'room', 'sanitary_fixture', 'wall', 'column', 'beam', 'stair', 'storey', 'floor'];

export function canonicalCategory(value) {
  const key = String(value || '').toLowerCase().replace(/[^a-z]/g, '');
  const aliases = {
    ifcdoor: 'door', scheduledoor: 'door', doorswing: 'door', doors: 'door',
    ifcwindow: 'window', windows: 'window',
    unit: 'apartment', units: 'apartment', apartments: 'apartment', residentialunit: 'apartment',
    washbasin: 'sink', washbasins: 'sink', sinks: 'sink', toilets: 'toilet', wc: 'toilet',
    bathtubs: 'bathtub', showers: 'shower', bedrooms: 'bedroom', kitchens: 'kitchen',
    balconies: 'balcony', saunas: 'sauna', bathrooms: 'bathroom',
    ifcspace: 'room', space: 'room', spaces: 'room', scheduleroom: 'room', rooms: 'room',
    ifcsanitaryterminal: 'sanitary_fixture', sanitaryfixture: 'sanitary_fixture', sanitaryfixtures: 'sanitary_fixture',
    ifcwall: 'wall', ifcwallstandardcase: 'wall', walls: 'wall',
    ifccolumn: 'column', columns: 'column', ifcbeam: 'beam', beams: 'beam',
    ifcstair: 'stair', ifcstairflight: 'stair', stairs: 'stair',
    ifcbuildingstorey: 'storey', storeys: 'storey', stories: 'storey',
  };
  return aliases[key] || reviewCategories.find(category => category.replaceAll('_', '') === key) || null;
}

export function countedCategory(answer) {
  const explicit = canonicalCategory(answer?.category || answer?.calculation?.category);
  if (explicit) return explicit;
  const evidence = originalEvidence(answer);
  const categories = new Set(evidence.map(item => canonicalCategory(item.category || item.type)));
  if (evidence.length && categories.size === 1 && !categories.has(null)) return [...categories][0];
  const classes = answer?.calculation?.classes;
  if (Array.isArray(classes)) {
    const specific = classes.filter(value => !String(value).startsWith('Ifc')).map(canonicalCategory).filter(Boolean);
    if (specific.length === 1) return specific[0];
    const resolved = new Set(classes.map(canonicalCategory));
    if (resolved.size === 1 && !resolved.has(null)) return [...resolved][0];
  }
  return null;
}

export function allowedCountCategories(answer) {
  const explicit = Array.isArray(answer?.allowed_count_categories) ? answer.allowed_count_categories : String(answer?.category || '').split('+');
  const categories = [...new Set(explicit.map(canonicalCategory).filter(Boolean))];
  const single = countedCategory(answer);
  return categories.length ? categories : single ? [single] : [];
}

export function usageLabel(answer) {
  const usage = answer?.usage;
  if (answer?.method?.startsWith('calibrated_')) return 'Calibrated measurement';
  if (usage?.cache_hit) return 'Saved answer reused';
  if (answer?.inventory_cache_hit || usage?.inventory_cache_hit) return 'Prepared visual inventory reused';
  return Number.isFinite(usage?.model_calls) && usage.model_calls === 0 ? 'Native source tools' : 'Model analysis';
}


export function evidenceVerificationText(item) {
  const checks = item?.verification;
  if (!checks) return [];
  const messages = [];
  if (checks.identity === true) messages.push('Source identifier exists.');
  if (checks.quote === true) messages.push('Quoted text matches the source.');
  if (checks.quote === false) messages.push('Quoted text was not verified against the source.');
  if (checks.quantity === true) messages.push('Quantity matches a compatible source value.');
  if (checks.quantity === false) messages.push('Quantity is not supported by the cited source.');
  if (checks.semantic_selection_verified === false) messages.push('Object selection and count completeness still require review.');
  return messages;
}


export function canResolveComparison(answer) {
  const comparison = answer?.reconciliation;
  return answer?.source_changed !== true && !!comparison && ['agreement', 'disagreement'].includes(comparison.status)
    && Number.isFinite(comparison.native_value) && Number.isFinite(comparison.visual_value);
}


// Presentation only: persisted quantities and exported source values keep full precision.
export function formatQuantityValue(value, unit) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return value == null ? '' : String(value);
  if (unit === 'count') return String(value);
  if (value !== 0 && Math.abs(value) < .001) return new Intl.NumberFormat('en-US', { useGrouping: false, maximumSignificantDigits: 4 }).format(value);
  return new Intl.NumberFormat('en-US', { useGrouping: false, maximumFractionDigits: 3 }).format(value);
}

// Display conversion only. The source quantity and its unit stay unchanged.
const imperialUnits = { 'm²': ['ft²', 10.7639], 'm2': ['ft²', 10.7639], 'm': ['ft', 3.28084], 'cm': ['in', 0.393701], 'mm': ['in', 0.0393701], 'm³': ['ft³', 35.3147] };

export function displayQuantity(value, unit, system = 'metric') {
  const numeric = typeof value === 'number' ? value : Number(value);
  const conversion = imperialUnits[String(unit ?? '').trim()];
  if (system !== 'imperial' || !conversion || typeof value !== 'number' || !Number.isFinite(numeric)) return { value, unit };
  return { value: numeric * conversion[1], unit: conversion[0] };
}
