import React from 'react';
import { inferenceCost, messageCost, usageNumber } from './inferenceUsage.js';
import { Divider } from './boardui/primitives.jsx';
import './InferenceCost.css';

export function MessageInferenceCost({ usage, label = 'This message' }) {
  return <div className="message-inference-cost" aria-label={`${label} inference cost`}>
    <span>{label}</span><strong>{messageCost(usage)}</strong>
  </div>;
}

export default function InferenceCost({ snapshot, unavailable }) {
  const usage = snapshot?.aggregate;
  const cost = inferenceCost(usage);
  const messages = Array.isArray(snapshot?.by_message) ? snapshot.by_message.slice().reverse() : [];
  return <section className="session-inference" aria-label="Current session inference cost">
    <div className="session-inference-heading"><span>Session inference</span><strong aria-live="polite">{usage ? cost.text : unavailable ? 'Unavailable' : 'Loading…'}</strong></div>
    <div className="session-inference-metrics"><span>{usageNumber(usage?.model_calls)} model calls</span><span>{usageNumber(usage && Number.isFinite(usage.input_tokens) && Number.isFinite(usage.output_tokens) ? usage.input_tokens + usage.output_tokens : null)} tokens</span></div>
    <p>{unavailable ? usage ? 'Usage could not refresh. The last recorded total is shown.' : 'Session usage is unavailable on this server.' : 'Estimate before credits. Hosting is separate.'}</p>
    {messages.length > 0 && <details className="session-message-details"><summary>{snapshot.message_count ?? messages.length} session messages</summary>
      <Divider />
      <ol>{messages.map(item => <li key={item.request_id || item.message_id || item.answer_id}>
        <div><span>{item.question || 'Drawing question'}</span><strong>{['pending', 'running', 'in_progress'].includes(item.status) ? 'In progress' : messageCost(item.usage)}</strong></div>
        <small>{item.status === 'error' || item.status === 'failed' ? 'Request failed' : item.status === 'pending' ? 'Server request is still running' : `${usageNumber(item.usage?.model_calls)} model calls`}</small>
      </li>)}</ol>
    </details>}
  </section>;
}
