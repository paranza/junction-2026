// A successful save is authoritative; it must not depend on another history GET.
export async function attachChatDrawing(request, { active, documentId, identity }) {
  const response = await request('/api/workspace/attachments', 'POST', {
    session_id: active, next_session_id: identity, document_id: documentId,
  });
  if (!response.thread?.id || response.thread.document_id !== documentId) throw new Error('The chat service did not confirm the drawing attachment');
  return { thread: response.thread, switched: response.thread.id !== active };
}
