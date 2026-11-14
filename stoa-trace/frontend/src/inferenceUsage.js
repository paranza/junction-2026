const SESSION_KEY = 'trace.inference-session.v1';
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const amount = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
let memorySession;

export function inferenceSessionId(storage, createId = () => crypto.randomUUID()) {
  try {
    const saved = storage?.getItem(SESSION_KEY);
    if (uuid.test(saved || '')) return saved;
  } catch { /* Private browsing can disable storage; keep a tab-local fallback. */ }
  if (!memorySession) memorySession = createId();
  try { storage?.setItem(SESSION_KEY, memorySession); } catch { /* In-memory identity remains stable. */ }
  return memorySession;
}

export function requestFailure(body, status) {
  const detail = body && typeof body === 'object' ? body.detail : null;
  const message = typeof body === 'string' ? body : detail?.message || (typeof detail === 'string' ? detail : null)
    || body?.error?.message || (typeof body?.error === 'string' ? body.error : null) || `Request failed (${status})`;
  const error = new Error(message);
  error.status = status;
  error.usage = detail?.usage || body?.usage || null;
  error.messageId = detail?.message_id || body?.message_id || null;
  return error;
}

export function money(value) {
  if (!amount(value)) return 'Unknown';
  if (value === 0) return '$0';
  if (value < .0001) return '<$0.0001';
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: value < 1 ? 4 : 2, maximumFractionDigits: value < 1 ? 4 : 2 })}`;
}

export function inferenceCost(usage) {
  if (!usage) return { text: 'Cost unknown', unknown: true };
  if (usage.usage_incomplete || !amount(usage.cost_estimate_usd)) {
    return { text: amount(usage.cost_known_usd) ? `${money(usage.cost_known_usd)} known + unknown` : 'Cost unknown', unknown: true };
  }
  return { text: money(usage.cost_estimate_usd), unknown: false };
}

export function messageCost(usage) {
  const result = inferenceCost(usage);
  if (result.unknown) return result.text;
  if (usage.cache_hit) return `${result.text} · cached`;
  if (usage.model_calls === 0) return `${result.text} · no model calls`;
  return `${result.text} estimated`;
}

export function acceptUsageSnapshot(current, next, sessionId) {
  if (!next || next.session_id !== sessionId || !Number.isSafeInteger(next.revision) || next.revision < 0
      || !next.aggregate || typeof next.aggregate !== 'object') return current;
  if (current?.session_id === sessionId && current.revision > next.revision) return current;
  return next;
}

export function usagePending(snapshot) {
  return Array.isArray(snapshot?.by_message) && snapshot.by_message.some(item => ['pending', 'running', 'in_progress'].includes(item.status));
}

export function usageNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value.toLocaleString() : '—';
}
