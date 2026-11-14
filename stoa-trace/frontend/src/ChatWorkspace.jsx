import React, { useEffect, useState, useRef } from 'react';
import { loadChatWorkspace } from './chatLoading.js';

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
  const choose = id => { selectionVersion.current++; setActive(id); remember(id); location.hash = 'chats'; };
  const create = async (projectId = null) => {
    selectionVersion.current++;
    try { const r = await api('/api/workspace/chats', 'POST', { name: 'New chat', project_id: projectId }); await refresh(); choose(r.id); }
    catch { setError('The chat could not be created. Please retry.'); }
  };
  const document = async id => {
    selectionVersion.current++;
    try {
      const current = data.threads.find(t => t.id === active);
      if (current?.document_id && current.document_id !== id) {
        const existing = data.threads.find(t => t.document_id === id && t.project_id === current.project_id);
        if (existing) { choose(existing.id); return true; }
        const r = await api('/api/workspace/chats', 'POST', { name: 'Floor plan', document_id: id, project_id: current.project_id });
        await refresh(); choose(r.id); return true;
      }
      if (!current) await api('/api/workspace/chats', 'POST', { name: 'Floor plan', document_id: id, session_id: active });
      else await api(`/api/workspace/chats/${active}`, 'PATCH', { document_id: id });
      await refresh(); return false;
    } catch { setError('The drawing could not be attached to this chat. Please retry.'); return true; }
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
  return <>{error && <div className="workspace-global-error" role="status">{error} <button onClick={() => setRetry(v => v + 1)}>Retry</button></div>}<App key={active} thread={thread} chatWorkspace={{ ...data, active, choose, create, document, rename, project, historyUnavailable, reconnect: () => setRetry(v => v+1) }} /></>;
}
export function ThreadActions({ thread, workspace }) {
  const [open, setOpen] = useState(false), [name, setName] = useState('');
  return <div className="thread-actions"><button className="thread-options-button" aria-label="Chat options" aria-expanded={open} onClick={() => { setName(thread.title); setOpen(v => !v); }}>•••</button>{open && <div className="thread-options"><form onSubmit={e => { e.preventDefault(); if (name.trim()) { workspace.rename(name.trim()); setOpen(false); } }}><label>Chat name<input value={name} onChange={e => setName(e.target.value)} maxLength={160} /></label><button type="submit">Save name</button></form><label>Project<select value={thread.project_id || ''} onChange={e => workspace.rename(undefined, e.target.value)}><option value="">No project</option>{workspace.projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><button onClick={() => setOpen(false)}>Done</button></div>}</div>;
}
