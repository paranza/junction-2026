import React, { useEffect, useState, useRef } from 'react';
import { loadChatWorkspace } from './chatLoading.js';
import { attachChatDrawing } from './chatAttachment.js';

const validId = value => /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value || '');
const api = async (path, method = 'GET', body) => {
  const response = await fetch(path, { method, cache: 'no-store', ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) });
  if (!response.ok) throw new Error(`Chat service returned ${response.status}`);
  return response.json();
};
const initialId = () => {
  try { const id = localStorage.getItem('metria.active-thread.v1'); if (validId(id)) return id; } catch {}
  return crypto.randomUUID();
};
const readIndex = () => { try { const value=JSON.parse(localStorage.getItem('metria.chat-index.v1') || 'null'); if(Array.isArray(value?.projects)&&Array.isArray(value?.threads)) return value; } catch {} return {projects:[],threads:[]}; };
const saveIndex = value => { try { localStorage.setItem('metria.chat-index.v1',JSON.stringify(value)); } catch {} };
export default function ChatWorkspace({ App }) {
  const [data, setData] = useState(readIndex);
  const [active, setActive] = useState(initialId);
  const [error, setError] = useState('');
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [retry, setRetry] = useState(0);
  const selectionVersion = useRef(0);
  const retryAttachment = useRef(null);
  const remember = id => { try { localStorage.setItem('metria.active-thread.v1', id); } catch {} };
  const refresh = async () => {
    const next = await api('/api/workspace/chats');
    if (!Array.isArray(next.threads) || !Array.isArray(next.projects)) throw new Error('Invalid chat service response');
    setData(next); saveIndex(next); setError(''); setHistoryUnavailable(false); return next;
  };
  useEffect(() => {
    let live = true;
    const load = async () => {
      const version = selectionVersion.current;
      const next = await loadChatWorkspace(api, { active: () => live });
      if (!live || version !== selectionVersion.current) return;
      if (!next) { setHistoryUnavailable(true); return; }
      setData(next); saveIndex(next); setError(''); setHistoryUnavailable(false);
      setActive(current => {
        const id = next.threads.some(t => t.id === current) ? current : next.threads[0]?.id || current;
        remember(id); return id;
      });
    };
    load();
    window.addEventListener('focus', load);
    return () => { live = false; window.removeEventListener('focus', load); };
  }, [retry]);
  const choose = id => { selectionVersion.current++; setActive(id); remember(id); setError(''); retryAttachment.current = null; location.hash = 'chats'; };
  const create = async (projectId = null) => {
    selectionVersion.current++;
    try { const r = await api('/api/workspace/chats', 'POST', { name: 'New chat', project_id: projectId }); await refresh(); choose(r.id); }
    catch { setError('The chat could not be created. Please retry.'); }
  };
  const document = async (id, identity = crypto.randomUUID()) => {
    selectionVersion.current++;
    try {
      const result = await attachChatDrawing(api, { threads: data.threads, active, documentId: id, identity });
      setData(current => {
        const next = { ...current, threads: [result.thread, ...current.threads.filter(t => t.id !== result.thread.id)] };
        saveIndex(next); return next;
      });
      setError(''); retryAttachment.current = null;
      // Remount on a newly attached drawing so a retried save opens it too.
      choose(result.thread.id);
      return result.switched;
    } catch {
      retryAttachment.current = () => document(id, identity);
      setError('The drawing could not be attached to this chat.'); return true;
    }
  };
  const rename = async (title, projectId) => {
    selectionVersion.current++;
    try {
      await api(`/api/workspace/chats/${active}`, 'PATCH', { ...(title ? { title } : {}), ...(projectId !== undefined ? { project_id: projectId } : {}) });
      await refresh();
    } catch { setError('The chat changes could not be saved.'); }
  };
  const project = async name => {
    selectionVersion.current++;
    try { const r = await api('/api/workspace/projects', 'POST', { name }); await refresh(); await create(r.id); }
    catch { setError('The project could not be created.'); }
  };
  const thread = data.threads.find(t => t.id === active) || { id: active, title: 'New chat', document_id: null, project_id: null };
  return <>{error && <div className="workspace-global-error" role="status">{error} <button onClick={() => retryAttachment.current ? retryAttachment.current() : setRetry(v => v + 1)}>Retry</button></div>}<App key={`${active}:${thread.document_id || ''}`} thread={thread} chatWorkspace={{ ...data, active, choose, create, document, rename, project, historyUnavailable, reconnect: () => setRetry(v => v+1) }} /></>;
}
export function ThreadActions({ thread, workspace }) {
  const [open, setOpen] = useState(false), [name, setName] = useState('');
  return <div className="thread-actions"><button className="thread-options-button" aria-label="Chat options" aria-expanded={open} onClick={() => { setName(thread.title); setOpen(v => !v); }}>•••</button>{open && <div className="thread-options"><form onSubmit={e => { e.preventDefault(); if (name.trim()) { workspace.rename(name.trim()); setOpen(false); } }}><label>Chat name<input value={name} onChange={e => setName(e.target.value)} maxLength={160} /></label><button type="submit">Save name</button></form><label>Project<select value={thread.project_id || ''} onChange={e => workspace.rename(undefined, e.target.value)}><option value="">No project</option>{workspace.projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><button onClick={() => setOpen(false)}>Done</button></div>}</div>;
}
