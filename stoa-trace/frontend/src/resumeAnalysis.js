// A resumed inspection must keep the original question and exact source scope.
// Current page/selection controls may have changed since that answer was saved.
export function resumeAnalysisRequest(answer, selectedDocumentId) {
  if (answer?.retryable_analysis !== true || answer.source_changed || !answer.document_id
      || String(answer.document_id) !== String(selectedDocumentId)) return null;
  const context = answer.request_context;
  if (!context || String(context.document_id) !== String(answer.document_id)
      || !Number.isInteger(context.page) || context.page < 1
      || !['page', 'document'].includes(context.scope)
      || typeof answer.question !== 'string' || !answer.question.trim()) return null;
  const region = context.region;
  if (region != null && (!Array.isArray(region) || region.length !== 4
      || !region.every(v => Number.isFinite(v) && v >= 0 && v <= 1)
      || region[0] >= region[2] || region[1] >= region[3])) return null;
  return { document_id: answer.document_id, question: answer.question,
    page: context.page, scope: context.scope, ...(region ? { region: [...region] } : {}) };
}
