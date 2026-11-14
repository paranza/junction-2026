import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, LoaderCircle } from 'lucide-react';
import { messageCost } from './inferenceUsage.js';
import { formatQuantityValue } from './reviewState.js';
import { acceptHydratedAnswer, mergeConversation, pendingAnswerIds, readConversation, recordFromAnswer, recordsFromSnapshot, saveConversation } from './conversationState.js';

export function useConversation({ sessionId, snapshot, answer, answerQuestion, documentName, request }) {
  const [records, setRecords] = useState(() => {
    try { return readConversation(window.sessionStorage, sessionId); } catch { return []; }
  });
  const [answers, setAnswers] = useState({});
  const answersRef = useRef(answers);
  const unavailable = useRef(new Set());
  const [unavailableIds, setUnavailableIds] = useState([]);
  useEffect(() => {
    setRecords(current => mergeConversation(current, recordsFromSnapshot(snapshot, sessionId)));
  }, [snapshot, sessionId]);
  useEffect(() => {
    if (!answer?.id) return;
    setRecords(current => mergeConversation(current, [recordFromAnswer(answer, answerQuestion, documentName)]));
    setAnswers(current => { const next = { ...current, [answer.id]: answer }; answersRef.current = next; return next; });
  }, [answer, answerQuestion, documentName]);
  useEffect(() => {
    try { saveConversation(window.sessionStorage, sessionId, records); } catch { /* In-memory transcript remains usable. */ }
  }, [sessionId, records]);
  const recordIds = records.map(record => `${record.status}:${record.answerId || record.id}`).join('|');
  useEffect(() => {
    const controller = new AbortController();
    const allowed = new Set(records.map(record => record.answerId).filter(Boolean));
    if (Object.keys(answersRef.current).some(id => !allowed.has(id))) {
      const retained = Object.fromEntries(Object.entries(answersRef.current).filter(([id]) => allowed.has(id)));
      answersRef.current = retained; setAnswers(retained);
    }
    const queue = pendingAnswerIds(records, answersRef.current, unavailable.current);
    const work = async () => {
      while (queue.length && !controller.signal.aborted) {
        const id = queue.shift();
        try {
          const result = await request(`/api/answers/${encodeURIComponent(id)}`, { signal: controller.signal });
          if (controller.signal.aborted) return;
          if (result?.id !== id) throw new Error('Saved answer identity does not match');
          setAnswers(current => { const next = acceptHydratedAnswer(current, id, result); answersRef.current = next; return next; });
        } catch (error) {
          if (controller.signal.aborted || error.name === 'AbortError') return;
          unavailable.current.add(id); setUnavailableIds([...unavailable.current]);
        }
      }
    };
    Promise.allSettled(Array.from({ length: Math.min(4, queue.length) }, work));
    return () => controller.abort();
  }, [recordIds, request]);
  const usageById = snapshot?.session_id === sessionId ? Object.fromEntries((snapshot.by_message || []).map(item => [item.message_id || item.request_id, item.usage])) : {};
  return { records, answers, unavailableIds, usageById };
}

export default function ChatThread({ conversation, activeAnswer, asking, onInspect, children, quantityUnit }) {
  return <div className="chat-thread" aria-label="Conversation messages">
    {conversation.records.length === 24 && <p className="chat-thread-limit">Showing the 24 most recent questions in this session.</p>}
    {conversation.records.map(record => {
      if (asking && ['pending', 'running', 'in_progress'].includes(record.status)) return null;
      const response = conversation.answers[record.answerId];
      const active = !asking && activeAnswer?.id === record.answerId;
      return <article className={`chat-turn ${active ? 'is-active' : ''}`} key={record.id}>
        <div className="chat-user-message"><span className="chat-user-label">You</span><p>{record.question}</p>{(response?.document?.name || record.documentName) && <span className="chat-user-context">{response?.document?.name || record.documentName}</span>}</div>
        {active ? children : <div className="chat-assistant-message">
          <span className="chat-assistant-label">Metria</span>
          {response ? <>{response.source_changed && <p className="chat-message-source-state" role="status">Source changed. Recompute this answer before using it.</p>}<p className="chat-message-summary">{response.value != null && <strong>{formatQuantityValue(response.value, response.unit)} {quantityUnit(response) || ''}</strong>}{response.answer || response.message || 'Saved answer'}</p><div className="chat-message-actions"><span className="chat-message-cost">{messageCost(response.usage)}</span><button type="button" onClick={() => onInspect({ id: response.id, question: record.question, documentId: response.document_id, documentName: response.document?.name || record.documentName })}>Inspect answer <ArrowUpRight size={14} /></button></div></> : ['error', 'failed'].includes(record.status) ? <><p className="chat-message-summary">This question could not be completed.</p><span className="chat-message-cost">{messageCost(conversation.usageById[record.id])}</span></> : conversation.unavailableIds.includes(record.answerId) ? <p className="chat-message-summary">This saved answer is unavailable.</p> : <p className="chat-message-loading"><LoaderCircle size={14} className="spin" />{record.status === 'completed' ? 'Opening saved answer…' : 'The server is still working on this question…'}</p>}
        </div>}
      </article>;
    })}
    {activeAnswer && !asking && !conversation.records.some(record => record.answerId === activeAnswer.id) && <article className="chat-turn is-active"><div className="chat-user-message"><span className="chat-user-label">You</span><p>{activeAnswer.question}</p></div>{children}</article>}
  </div>;
}
