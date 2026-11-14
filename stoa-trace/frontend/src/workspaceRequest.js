export async function workspaceRequest(path, method = 'GET', body, { fetcher = fetch, timeoutMs = 15000, signal } = {}) {
  let response;
  try {
    response = await fetcher(path, {
      method, cache: 'no-store', signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs),
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (cause) {
    if (signal?.aborted) throw cause;
    throw new Error(cause.name === 'TimeoutError' || cause.name === 'AbortError'
      ? 'The local server did not respond in time. Retry the operation.'
      : 'Cannot reach the local server. Check that the app is running.');
  }
  if (!response.ok) {
    const messages = {401:'The server requires an authorized project connection.',404:'The requested drawing or chat was not found.',409:'The chat changed while saving. Retry the operation.',422:'The server rejected this request. Reload the app and retry.'};
    const error = new Error(`${messages[response.status] || 'The server could not complete this request.'} (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }
  if (!(response.headers.get('content-type') || '').includes('application/json')) {
    throw new Error('The server returned a page instead of chat data. Reload the app.');
  }
  try { return await response.json(); }
  catch { throw new Error('The server returned unreadable chat data. Retry the operation.'); }
}
