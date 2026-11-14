export function readChatWorkspaceIndex(storage) {
  try {
    const value = JSON.parse(storage.getItem('metria.chat-index.v1') || 'null');
    const validId = id => typeof id === 'string' && /^[a-f0-9-]{36}$/i.test(id);
    if (Array.isArray(value?.projects) && Array.isArray(value?.threads)
      && value.projects.every(project => validId(project?.id) && typeof project.name === 'string')
      && value.threads.every(thread => validId(thread?.id) && typeof thread.title === 'string')) return value;
  } catch {}
  return { projects: [], threads: [] };
}

export async function loadChatWorkspace(request, { active = () => true, delay = ms => new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
  for (let attempt = 0; attempt < 3 && active(); attempt++) {
    try {
      const data = await request('/api/workspace/chats');
      if (!Array.isArray(data?.threads) || !Array.isArray(data?.projects)) throw new Error('Invalid chat response');
      return active() ? data : null;
    } catch {
      if (attempt < 2 && active()) await delay(500);
    }
  }
  return null;
}
