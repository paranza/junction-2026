// Display only recorded analysis roles. A model review is never a truth label.
const visualMethods = new Set(['vision', 'visual_inventory']);
const recordedModel = value => typeof value === 'string' && value.trim() ? value.trim().slice(0, 160) : null;

export function modelDisplayName(value) {
  const model = recordedModel(value);
  if (!model) return 'Model not recorded';
  const name = model.split('/').at(-1);
  const known = {
    'gemini-4-carbon': 'Gemini 4 Carbon',
    'gemini-4-argon': 'Gemini 4 Argon',
    'gemini-4-hydrogen': 'Gemini 4 Hydrogen',
    'gemma-4-31b-it': 'Gemma 4 31B',
    'gemma-4-26b-a4b-it': 'Gemma 4 26B A4B',
    'gpt-6-astra': 'GPT-6 Astra',
  };
  return known[name] || name.replaceAll('_', ' ').replaceAll('-', ' ');
}

export function analysisProvenance(answer) {
  // Translation usage and a configured provider do not turn native quantities
  // or a user-calibrated measurement into visual-model analysis.
  if (!visualMethods.has(answer?.method)) return null;
  const audit = answer?.count_audit && typeof answer.count_audit === 'object' ? answer.count_audit : null;
  const usageModels = Array.isArray(answer?.usage?.models) ? answer.usage.models.filter(recordedModel) : [];
  const initial = recordedModel(audit?.initial_model) || recordedModel(answer.model)
    || (usageModels.length === 1 && !audit ? recordedModel(usageModels[0]) : null);
  const reviewer = audit ? recordedModel(audit.auditor_model) || recordedModel(audit.model) : null;
  const status = audit?.status;
  const statusText = audit ? ({
    completed: 'Review completed',
    unavailable: 'Review unavailable',
    incomplete: 'Review incomplete',
    incomplete_scope: 'Scope incomplete',
  })[status] || 'Review status unavailable' : null;
  const isCount = answer.operation === 'count' || answer.unit === 'count';
  const count = value => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
  const before = audit?.initial_value ?? answer.original_detection?.value;
  const after = audit?.audited_value;
  const changed = isCount && status === 'completed' && count(before) && count(after) && before !== after;
  return {
    analysisModel: modelDisplayName(initial),
    reviewer: reviewer ? modelDisplayName(reviewer) : null,
    reviewerLabel: status === 'completed' || status === 'incomplete' ? 'Source-image reviewer' : 'Selected reviewer',
    statusText,
    changedCounts: changed ? { before, after } : null,
    note: audit ? 'Model review; inspect the highlighted evidence.' : 'Inspect the highlighted visual candidates.',
  };
}
