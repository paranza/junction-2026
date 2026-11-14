import React, { useEffect, useState, useRef } from 'react';
import { loadChatWorkspace, readChatWorkspaceIndex } from './chatLoading.js';
import { attachChatDrawing } from './chatAttachment.js';
import { workspaceRequest as api } from './workspaceRequest.js';

const validId = value => /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value || '');
const initialId = () => {
  try { const id = localStorage.getItem('metria.active-thread.v1'); if (validId(id)) return id; } catch {}
  return crypto.randomUUID();
};
const readIndex = () => { try { return readChatWorkspaceIndex(localStorage); } catch { return {projects:[],threads:[]}; } };
const saveIndex = value => { try { localStorage.setItem('metria.chat-index.v1',JSON.stringify(value)); } catch {} };
export default function ChatWorkspace({ App }) {
  const [data, setData] = useState(readIndex);
  const [active, setActive] = useState(initialId);
  const [error, setError] = useState('');
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [retry, setRetry] = useState(0);
  const selectionVersion = useRef(0);
  const failedOperation = useRef(null);
  const remember = id => { try { localStorage.setItem('metria.active-thread.v1', id); } catch {} };
  const saveThread = thread => setData(current => {
    const next = { ...current, threads: [thread, ...current.threads.filter(t => t.id !== thread.id)] };
    saveIndex(next); return next;
  });
  const fail = (message, cause, retryOperation) => {
    failedOperation.current = retryOperation;
    setError(`${message} ${cause.message}`);
  };
  useEffect(() => {
    let live = true;
    let loadSequence = 0;
    const load = async () => {
      const sequence = ++loadSequence;
      const version = selectionVersion.current;
      const next = await loadChatWorkspace(api, { active: () => live });
      if (!live || sequence !== loadSequence || version !== selectionVersion.current) return;
      if (!next) { setHistoryUnavailable(true); return; }
      setData(next); saveIndex(next); setHistoryUnavailable(false);
      setActive(current => {
        const id = next.threads.some(t => t.id === current) ? current : next.threads[0]?.id || current;
        remember(id); return id;
      });
    };
    load();
    window.addEventListener('focus', load);
    return () => { live = false; window.removeEventListener('focus', load); };
  }, [retry]);
  const choose = id => { selectionVersion.current++; setActive(id); remember(id); setError(''); failedOperation.current = null; location.hash = 'chats'; };
  const create = async (projectId = null, identity = crypto.randomUUID()) => {
    const version = ++selectionVersion.current;
    try {
      const result = await api('/api/workspace/chats', 'POST', { name: 'New chat', project_id: projectId, session_id: identity });
      if (!result.thread?.id) throw new Error('The server did not confirm the new chat.');
      saveThread(result.thread);
      if (version === selectionVersion.current) choose(result.id);
    } catch (cause) { if (version === selectionVersion.current) fail('Chat not created.', cause, () => create(projectId, identity)); }
  };
  const document = async (id, identity = crypto.randomUUID()) => {
    const version = ++selectionVersion.current;
    try {
      const result = await attachChatDrawing(api, { active, documentId: id, identity });
      saveThread(result.thread);
      if (version !== selectionVersion.current) return true;
      choose(result.thread.id);
      return result.switched;
    } catch (cause) {
      if (version === selectionVersion.current) fail('Drawing not attached.', cause, () => document(id, identity));
      return true;
    }
  };
  const rename = async (title, projectId) => {
    const version = ++selectionVersion.current;
    try {
      const result = await api(`/api/workspace/chats/${active}`, 'PATCH', { ...(title ? { title } : {}), ...(projectId !== undefined ? { project_id: projectId } : {}) });
      if (!result.thread?.id) throw new Error('The server did not confirm the chat changes.');
      saveThread(result.thread);
      if (version === selectionVersion.current) { setError(''); failedOperation.current = null; }
    } catch (cause) { if (version === selectionVersion.current) fail('Chat changes not saved.', cause, () => rename(title, projectId)); }
  };
  const project = async (name, identity = crypto.randomUUID(), chatIdentity = crypto.randomUUID()) => {
    const version = ++selectionVersion.current;
    try {
      const result = await api('/api/workspace/projects', 'POST', { name, session_id: identity });
      if (!result.project?.id) throw new Error('The server did not confirm the project.');
      setData(current => {
        const next = { ...current, projects: [...current.projects.filter(p => p.id !== result.id), result.project] };
        saveIndex(next); return next;
      });
      const chat = await api('/api/workspace/chats', 'POST', { name: 'New chat', project_id: result.id, session_id: chatIdentity });
      if (!chat.thread?.id) throw new Error('The server did not confirm the project chat.');
      saveThread(chat.thread);
      if (version === selectionVersion.current) choose(chat.id);
    } catch (cause) { if (version === selectionVersion.current) fail('Project setup incomplete.', cause, () => project(name, identity, chatIdentity)); }
  };
  const thread = data.threads.find(t => t.id === active) || { id: active, title: 'New chat', document_id: null, project_id: null };
  return <>{error && <div className="workspace-global-error" role="status">{error} <button onClick={() => failedOperation.current ? failedOperation.current() : setRetry(v => v + 1)}>Retry</button></div>}<App key={`${active}:${thread.document_id || ''}`} thread={thread} chatWorkspace={{ ...data, active, choose, create, document, rename, project, historyUnavailable, reconnect: () => setRetry(v => v+1) }} /></>;
}
export function ThreadActions({ thread, workspace, onBrowse, onExport }) {
  const [open, setOpen] = useState(false), [name, setName] = useState('');
  return <div className="thread-actions"><button className="thread-options-button" aria-label="Chat options" aria-expanded={open} onClick={() => { setName(thread.title); setOpen(v => !v); }}>•••</button>{open && <div className="thread-options">{onBrowse && <button onClick={()=>{onBrowse();setOpen(false)}}>Browse uploads</button>}{onExport && <button onClick={()=>{onExport();setOpen(false)}}>Export quantities (CSV)</button>}<form onSubmit={e => { e.preventDefault(); if (name.trim()) { workspace.rename(name.trim()); setOpen(false); } }}><label>Chat name<input value={name} onChange={e => setName(e.target.value)} maxLength={160} /></label><button type="submit">Save name</button></form><button onClick={() => setOpen(false)}>Done</button></div>}</div>;
}
