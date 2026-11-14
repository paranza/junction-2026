import { evidenceBox, savedAdditions } from './reviewState.js';

export function closeupTarget(answer, evidence) {
  if (!answer?.id || answer.source_changed || evidence?.id == null || !evidenceBox(evidence)) return null;
  // The proxy rejects an invalid explicit box rather than switching source regions.
  if (evidence.bbox != null && !evidenceBox({ bbox: evidence.bbox })) return null;
  const saved = [...(answer.evidence || []), ...(answer.original_evidence || []), ...savedAdditions(answer)];
  if (!saved.some(item => String(item.id) === String(evidence.id))) return null;
  const answerId = String(answer.id), evidenceId = String(evidence.id);
  return {
    answerId, evidenceId,
    key: JSON.stringify([answerId, evidenceId, evidence.document_id, evidence.page, evidenceBox(evidence)]),
    path: `/api/answers/${encodeURIComponent(answerId)}/evidence/${encodeURIComponent(evidenceId)}/closeup`,
  };
}

export function protectedCloseupImage(payload) {
  if (payload?.provider !== 'cloudinary' || !/^\/api\/media\/[a-f0-9]{64}\.png$/.test(payload.image_url || '')) return null;
  if (![payload.width, payload.height].every(value => Number.isSafeInteger(value) && value > 0)) return null;
  return { src: payload.image_url, width: payload.width, height: payload.height };
}

// A response belongs only to the current attempt and selected source item.
export function closeupRequestGate() {
  let attempt = 0, active = true;
  return {
    begin: () => ++attempt,
    accepts: ticket => active && ticket === attempt,
    dispose: () => { active = false; attempt += 1; },
  };
}
