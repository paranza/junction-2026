export async function loadChatWorkspace(request, { active = () => true, delay = ms => new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
  for (let attempt = 0; attempt < 3 && active(); attempt++) {
    try {
      const data = await request('/api/chats');
      if (!Array.isArray(data?.threads) || !Array.isArray(data?.projects)) throw new Error('Invalid chat response');
      return active() ? data : null;
    } catch {
      if (attempt < 2 && active()) await delay(500);
    }
  }
  return null;
}
