export function usageValue(usage, metric) {
  if (!usage) return 0;
  if (metric === 'calls') return usage.model_calls || 0;
  if (metric === 'cost') return usage.cost_known_usd || 0;
  return (usage.input_tokens || 0) + (usage.output_tokens || 0);
}

export function spendingCoverage(usage) {
  const requests = usage?.model_calls || 0;
  const unpriced = usage?.cost_unavailable_calls || 0;
  return { requests, unpriced, priced: requests - unpriced, knownCost: usage?.cost_known_usd || 0 };
}
