// A successful save is authoritative; it must not depend on another history GET.
export async function attachChatDrawing(request, { threads, active, documentId, identity }) {
  const current = threads.find(thread => thread.id === active);
  const switched = Boolean(current?.document_id && current.document_id !== documentId);
  if (switched) {
    const existing = threads.find(thread => thread.document_id === documentId && thread.project_id === current.project_id);
    if (existing) return { thread: existing, switched: true };
  }
  const response = !current || switched
    ? await request('/api/workspace/chats', 'POST', {
        name: 'Floor plan', document_id: documentId, project_id: current?.project_id || null,
        session_id: switched ? identity : active,
      })
    : await request(`/api/workspace/chats/${active}`, 'PATCH', { document_id: documentId });
  if (!response.thread?.id) throw new Error('The chat service did not confirm the drawing attachment');
  return { thread: response.thread, switched };
}
