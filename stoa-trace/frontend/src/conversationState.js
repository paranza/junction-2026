const MAX_TURNS = 24;
const safeId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const states = new Set(['pending', 'running', 'in_progress', 'completed', 'error', 'failed']);
const terminal = status => ['completed', 'error', 'failed'].includes(status);

function cleanRecord(value) {
  if (!value || !safeId(value.id) || typeof value.question !== 'string' || !value.question.trim()
      || !Number.isFinite(value.timestamp) || value.timestamp < 0 || !states.has(value.status)) return null;
  return { id: value.id, answerId: safeId(value.answerId) ? value.answerId : null,
    question: value.question.slice(0, 2500), timestamp: value.timestamp,
    status: value.status, documentName: typeof value.documentName === 'string' ? value.documentName.slice(0, 512) : '' };
}

export const conversationKey = sessionId => `trace.conversation.v1:${sessionId}`;

export function readConversation(storage, sessionId) {
  try {
    const value = JSON.parse(storage?.getItem(conversationKey(sessionId)) || 'null');
    if (value?.version !== 1 || value.sessionId !== sessionId || !Array.isArray(value.records)) return [];
    return mergeConversation([], value.records);
  } catch { return []; }
}

export function saveConversation(storage, sessionId, records) {
  try { storage?.setItem(conversationKey(sessionId), JSON.stringify({ version: 1, sessionId, records: mergeConversation([], records) })); } catch { /* Session history can still work in memory. */ }
}

export function mergeConversation(current, incoming) {
  const records = new Map();
  for (const value of [...current, ...incoming]) {
    const record = cleanRecord(value);
    if (!record) continue;
    const previous = records.get(record.id);
    // Delayed pending metadata must never turn a completed answer back into a spinner.
    if (previous && terminal(previous.status) && !terminal(record.status)) continue;
    records.set(record.id, previous ? { ...record, timestamp: previous.timestamp, documentName: record.documentName || previous.documentName } : record);
  }
  const result = [...records.values()].sort((a, b) => a.timestamp - b.timestamp || a.id.localeCompare(b.id)).slice(-MAX_TURNS);
  return JSON.stringify(result) === JSON.stringify(current) ? current : result;
}

export function recordsFromSnapshot(snapshot, sessionId) {
  if (snapshot?.session_id !== sessionId || !Array.isArray(snapshot.by_message)) return [];
  return snapshot.by_message.map(item => ({ id: item.message_id || item.request_id, answerId: item.answer_id,
    question: item.question, timestamp: Number(item.created_at) * 1000, status: item.status }));
}

export function recordFromAnswer(answer, fallbackQuestion = '', documentName = '') {
  if (!safeId(answer?.id)) return null;
  const created = answer.created_at;
  const timestamp = typeof created === 'number' ? created < 1e12 ? created * 1000 : created : Date.parse(created);
  return { id: answer.message_id || answer.id, answerId: answer.id, question: answer.question || fallbackQuestion,
    timestamp: Number.isFinite(timestamp) ? timestamp : Date.now(), status: 'completed', documentName: answer.document?.name || documentName };
}

export function pendingAnswerIds(records, answers, unavailable = new Set()) {
  return records.filter(record => record.status === 'completed' && record.answerId && !answers[record.answerId] && !unavailable.has(record.answerId)).map(record => record.answerId);
}
